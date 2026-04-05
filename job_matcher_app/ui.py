import json
from dataclasses import dataclass

import pandas as pd
import streamlit as st
from sentence_transformers import util

from .config import APP_TITLE, SOURCE_OPTIONS


@dataclass
class PageContext:
    analyzer: object
    search_service: object
    quality_service: object
    database: object
    logger: object
    model: object


class BasePage:
    def __init__(self, context: PageContext):
        self.context = context

    def render(self):
        raise NotImplementedError


class JobsLookerPage(BasePage):
    def render(self):
        analyzer = self.context.analyzer
        search_service = self.context.search_service
        quality_service = self.context.quality_service
        database = self.context.database
        logger = self.context.logger
        model = self.context.model

        st.subheader("Jobs Looker")

        preloaded_resume = None
        if st.session_state.get("resume_id_to_load"):
            preloaded_resume = database.get_resume(int(st.session_state["resume_id_to_load"]))

        uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

        resume_name = None
        resume_text = None
        inferred_role = None
        confidence = 0.0
        resume_skills = []
        resume_id = None

        if uploaded_file:
            try:
                resume_text = analyzer.extract_text(uploaded_file)
                inferred_role, confidence = analyzer.infer_target_position(resume_text)
                resume_skills = sorted(analyzer.extract_skills(resume_text))
                resume_name = uploaded_file.name
                resume_id = database.save_resume(resume_name, resume_text, inferred_role, resume_skills)
                logger.info("resume_saved | name=%s | id=%s", resume_name, resume_id)
            except Exception as e:
                st.error(f"Could not read this PDF: {e}")
                st.stop()
        elif preloaded_resume is not None:
            resume_id = int(preloaded_resume["id"])
            resume_name = preloaded_resume["name"]
            resume_text = preloaded_resume["text_content"]
            inferred_role = preloaded_resume["inferred_role"]
            resume_skills = json.loads(preloaded_resume["skills_json"] or "[]")
            confidence = 0.95 if inferred_role else 0.0
            st.info(f"Using stored resume: {resume_name}")

        if not resume_text:
            st.info("Upload a resume to start matching jobs.")
            return

        fallback_query = analyzer.extract_search_query(resume_text)
        default_query = inferred_role if (inferred_role and confidence >= 0.20) else fallback_query

        with st.expander("Detected skills from your resume"):
            if resume_skills:
                self.render_keyword_boxes("Resume keywords", resume_skills, "#eef6ff", "#9ec5ff")
            else:
                st.write("No known skills detected yet. You can still run matching.")

        country_codes = analyzer.get_supported_countries()
        country_display_to_code = {code.replace("_", " ").title(): code for code in country_codes}
        country_display_options = sorted(country_display_to_code.keys())
        default_country = "Tunisia" if "Tunisia" in country_display_options else country_display_options[0]

        st.subheader("Search Parameters")
        col1, col2 = st.columns([3, 2])
        with col1:
            search_query = st.text_input("Detected target position", value=default_query)
        with col2:
            selected_countries = st.multiselect(
                "Countries",
                options=["All countries"] + country_display_options,
                default=[default_country],
            )

        col3, col4 = st.columns([1, 1])
        with col3:
            days = st.number_input("Days lookback", min_value=1, max_value=365, value=30, step=1)
        with col4:
            results_wanted = st.number_input("Max results", min_value=10, max_value=200, value=40, step=10)

        selected_labels = st.multiselect(
            "Job sources",
            options=list(SOURCE_OPTIONS.keys()),
            default=["LinkedIn", "Google Jobs", "Indeed"],
        )
        selected_sites = [SOURCE_OPTIONS[label] for label in selected_labels]

        if st.button("🔍 Find Current Jobs"):
            if not selected_sites:
                st.error("Please select at least one supported source.")
                st.stop()
            if not selected_countries:
                st.error("Please select at least one country.")
                st.stop()

            if "All countries" in selected_countries:
                target_country_codes = country_codes
            else:
                target_country_codes = [country_display_to_code[c] for c in selected_countries]

            target_countries_display = [code.replace("_", " ").title() for code in target_country_codes]

            with st.status("Running job search...", expanded=True) as status:
                st.write(
                    f"Searching for **{search_query}** in **{', '.join(target_countries_display)}** (last **{days}** days)"
                )
                logger.info(
                    "search_start | query=%s | countries=%s | days=%s | sources=%s | resume=%s",
                    search_query,
                    target_country_codes,
                    int(days),
                    selected_sites,
                    resume_name,
                )

                try:
                    jobs = search_service.search(search_query, target_country_codes, days, selected_sites, results_wanted)
                except Exception:
                    logger.exception("search_failed | query=%s", search_query)
                    st.error("Search failed. Try changing the query or sources.")
                    st.stop()

                if jobs.empty:
                    logger.warning("search_no_results | query=%s", search_query)
                    st.warning("No jobs found. Try another query, country, source, or larger day range.")
                    st.stop()

                raw_jobs = jobs.copy()
                jobs = jobs.dropna(subset=["title", "job_url"], how="any")
                jobs = jobs.drop_duplicates(subset=["title", "company", "job_url"], keep="first")
                quality_df = quality_service.build_checks(raw_jobs, jobs)

                jobs["match_score"] = 0.0
                if "description" in jobs.columns:
                    desc_df = jobs.dropna(subset=["description"]).copy()
                    if not desc_df.empty:
                        resume_emb = model.encode(resume_text[:5000], convert_to_tensor=True)
                        job_embs = model.encode(desc_df["description"].astype(str).tolist(), convert_to_tensor=True)
                        scores = util.cos_sim(resume_emb, job_embs)[0].cpu().tolist()
                        desc_df["match_score"] = scores
                        jobs.loc[desc_df.index, "match_score"] = desc_df["match_score"]

                ranked = jobs.sort_values(by=["match_score", "date_posted"], ascending=[False, False], na_position="last")
                search_run_id = database.save_search_run(
                    resume_id=resume_id,
                    query=search_query,
                    countries=", ".join(target_countries_display),
                    days=int(days),
                    sources=", ".join(selected_labels),
                    results_count=len(ranked),
                )
                database.save_quality_checks(search_run_id, quality_df)
                logger.info("search_done | resume_id=%s | run_id=%s | total_ranked=%s", resume_id, search_run_id, len(ranked))
                status.update(label=f"Done. Found {len(ranked)} listings.", state="complete")

            st.divider()
            st.success(f"Found {len(ranked)} current listings")

            st.subheader("Top matches (Top 5)")
            for _, row in ranked.head(5).iterrows():
                with st.container(border=True):
                    title = row.get("title", "Untitled role")
                    company = row.get("company", "Unknown company")
                    job_location = row.get("location", "Unknown location")
                    score = int(float(row.get("match_score", 0.0)) * 100)
                    st.markdown(f"### {title}")
                    st.write(f"**{company}** | {job_location}")
                    st.metric("Fit", f"{score}%")
                    if pd.notna(row.get("description", None)):
                        gap = analyzer.skill_gap_analysis(resume_text, str(row.get("description", "")))
                        col_a, col_b = st.columns(2)
                        with col_a:
                            self.render_keyword_boxes("Matching keywords", gap["matching_skills"][:12], "#ecfdf3", "#75d0a2")
                        with col_b:
                            self.render_keyword_boxes("Missing keywords", gap["missing_skills"][:12], "#fff1f2", "#f5a3ad")
                        with st.expander("Read Job Details"):
                            st.write(row.get("description", ""))
                    if pd.notna(row.get("job_url", None)):
                        st.link_button("Apply", str(row.get("job_url")))

            st.divider()
            st.subheader("All listings")
            display_cols = [
                c for c in ["title", "company", "location", "site", "date_posted", "match_score", "job_url"] if c in ranked.columns
            ]
            table_view = ranked[display_cols].copy()
            if "match_score" in table_view.columns:
                table_view["match_score"] = (table_view["match_score"] * 100).round(1)
                table_view = table_view.rename(columns={"match_score": "fit_%"})
            st.dataframe(table_view, use_container_width=True, hide_index=True)
            csv_data = table_view.to_csv(index=False).encode("utf-8")
            st.download_button("Download results as CSV", data=csv_data, file_name="job_matches.csv", mime="text/csv")

    @staticmethod
    def render_keyword_boxes(label, keywords, bg_color, border_color):
        st.caption(label)
        if not keywords:
            st.write("None")
            return
        chips = "".join(
            [
                f"<span style='display:inline-block; margin:3px 6px 3px 0; padding:4px 10px; border-radius:999px; "
                f"background:{bg_color}; border:1px solid {border_color}; font-size:0.82rem;'>{k}</span>"
                for k in keywords
            ]
        )
        st.markdown(chips, unsafe_allow_html=True)


class HistoryPage(BasePage):
    def render(self):
        database = self.context.database
        st.subheader("History & Data Quality")

        st.markdown("### Saved resumes")
        resumes = database.list_resumes()
        if resumes:
            for row in resumes:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.write(f"**{row['name']}**")
                        st.caption(f"Role: {row['inferred_role'] or 'N/A'} | Updated: {row['updated_at']}")
                    with c2:
                        if st.button("Check again", key=f"recheck_{row['id']}"):
                            st.session_state.resume_id_to_load = int(row["id"])
                            st.session_state.page_selector = "Jobs Looker"
                            st.rerun()
        else:
            st.info("No resumes saved yet.")

        st.markdown("### Search history")
        history_rows = database.get_search_history()
        if history_rows:
            st.dataframe(database.rows_to_df(history_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No search history yet.")

        st.markdown("### Data quality history")
        quality_rows = database.get_quality_history()
        if quality_rows:
            st.dataframe(database.rows_to_df(quality_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No data quality history yet.")
