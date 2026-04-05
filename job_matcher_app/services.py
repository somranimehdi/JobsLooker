import importlib
import re

import pandas as pd
import fitz
from jobspy import scrape_jobs
from sentence_transformers import util
from sklearn.feature_extraction.text import TfidfVectorizer

from .config import COUNTRY_FALLBACK, ROLE_CATALOG, SKILL_KEYWORDS


class ResumeAnalyzer:
    def __init__(self, model):
        self.model = model
        self.role_embeddings = self.model.encode(ROLE_CATALOG, convert_to_tensor=True)

    def extract_text(self, pdf_file):
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        raw_text = " ".join(page.get_text() for page in doc)
        return " ".join(raw_text.split())

    def extract_search_query(self, text):
        tfidf = TfidfVectorizer(stop_words="english", max_features=5, ngram_range=(1, 2))
        tfidf.fit_transform([text])
        return " ".join(tfidf.get_feature_names_out())

    def infer_target_position(self, resume_text):
        text_lower = resume_text.lower()
        keyword_scores = {}
        for role in ROLE_CATALOG:
            role_tokens = [tok for tok in re.findall(r"[a-zA-Z]+", role.lower()) if len(tok) > 2]
            score = sum(text_lower.count(tok) for tok in role_tokens)
            if score > 0:
                keyword_scores[role] = score

        if keyword_scores:
            best_keyword_role = max(keyword_scores, key=keyword_scores.get)
            if keyword_scores[best_keyword_role] >= 2:
                return best_keyword_role, 0.95

        snippet = resume_text[:3000] if len(resume_text) > 3000 else resume_text
        resume_emb = self.model.encode(snippet, convert_to_tensor=True)
        sims = util.cos_sim(resume_emb, self.role_embeddings)[0]
        best_idx = int(sims.argmax())
        return ROLE_CATALOG[best_idx], float(sims[best_idx])

    def extract_skills(self, text):
        if not text:
            return set()

        normalized = " " + text.lower() + " "
        found = set()
        for skill in SKILL_KEYWORDS:
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, normalized):
                found.add(skill)
        return found

    def skill_gap_analysis(self, resume_text, job_description):
        resume_skills = self.extract_skills(resume_text)
        job_skills = self.extract_skills(job_description)
        return {
            "matching_skills": sorted(job_skills & resume_skills),
            "missing_skills": sorted(job_skills - resume_skills),
        }

    def get_supported_countries(self):
        discovered = set()
        try:
            import jobspy

            def collect_country_values(namespace_obj):
                for attr in dir(namespace_obj):
                    if "country" not in attr.lower():
                        continue
                    value = getattr(namespace_obj, attr, None)
                    if isinstance(value, (list, tuple, set)):
                        for item in value:
                            if isinstance(item, str) and item.strip():
                                discovered.add(item.strip().lower())

            collect_country_values(jobspy)
            try:
                jobspy_constants = importlib.import_module("jobspy.constants")
                collect_country_values(jobspy_constants)
            except Exception:
                pass
        except Exception:
            pass

        cleaned = sorted([c for c in discovered if re.match(r"^[a-z_]+$", c)])
        return cleaned if cleaned else COUNTRY_FALLBACK


class JobSearchService:
    def __init__(self):
        self.scraper = scrape_jobs

    def search(self, search_term, countries, days, sources, results_wanted):
        jobs_frames = []
        per_country_results = max(10, int(results_wanted) // max(1, len(countries)))

        for country_code in countries:
            country_location = country_code.replace("_", " ").title()
            scrape_kwargs = {
                "site_name": sources,
                "search_term": search_term,
                "location": country_location,
                "results_wanted": per_country_results,
                "hours_old": int(days) * 24,
                "linkedin_fetch_description": True,
            }
            if "indeed" in sources:
                scrape_kwargs["country_indeed"] = country_code

            loc_jobs = self.scraper(**scrape_kwargs)
            if loc_jobs is not None and not loc_jobs.empty:
                jobs_frames.append(loc_jobs)

        return pd.concat(jobs_frames, ignore_index=True) if jobs_frames else pd.DataFrame()


class DataQualityService:
    def build_checks(self, raw_jobs, cleaned_jobs):
        total_raw = len(raw_jobs)
        total_clean = len(cleaned_jobs)
        missing_title_raw = int(raw_jobs["title"].isna().sum()) if "title" in raw_jobs.columns else total_raw
        missing_url_raw = int(raw_jobs["job_url"].isna().sum()) if "job_url" in raw_jobs.columns else total_raw
        duplicate_count = int(raw_jobs.duplicated(subset=["title", "company", "job_url"], keep="first").sum()) if all(
            c in raw_jobs.columns for c in ["title", "company", "job_url"]
        ) else 0

        return pd.DataFrame(
            [
                {"check": "Raw rows collected", "value": total_raw, "status": "OK" if total_raw > 0 else "FAIL"},
                {"check": "Rows after cleaning", "value": total_clean, "status": "OK" if total_clean > 0 else "FAIL"},
                {"check": "Missing title (raw)", "value": missing_title_raw, "status": "OK" if missing_title_raw == 0 else "WARN"},
                {"check": "Missing job URL (raw)", "value": missing_url_raw, "status": "OK" if missing_url_raw == 0 else "WARN"},
                {"check": "Duplicate rows removed", "value": duplicate_count, "status": "OK" if duplicate_count == 0 else "WARN"},
            ]
        )
