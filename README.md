# AI Resume-to-Jobs Matcher

A Streamlit app that uploads a resume, infers the target role, scrapes current job listings from public sources, and ranks matches with semantic similarity plus skill-gap highlights.

## What it does

- Upload one PDF resume at a time
- Detects the likely target role from the resume
- Scrapes live jobs from public sources via JobSpy
- Filters results by country and lookback window
- Ranks jobs by semantic fit
- Highlights matching and missing skills per job
- Stores resume data, search history, and data-quality checks in a local SQLite database
- Provides a separate history/data-quality page with a "Check again" action

## Features

- **Resume intelligence**
  - PDF text extraction with PyMuPDF
  - Role inference using keyword and semantic matching
  - Skill keyword extraction

- **Job matching**
  - Live scraping from LinkedIn, Google Jobs, and Indeed when supported by JobSpy
  - Country selection with an `All countries` option
  - Lookback window selection in days
  - Ranked results with semantic similarity scoring

- **Data quality and monitoring**
  - Raw vs cleaned row checks
  - Missing title / missing URL detection
  - Duplicate row detection
  - Search run history stored locally
  - Resume history stored locally
  - Logs written to `app_logs/job_matcher.log`

- **Clean architecture**
  - Button-based navigation
  - Separate pages for job search and history/data quality
  - Modular code split into services, database, UI, and app bootstrap

## Project structure

```text
JobFinder/
├── matcher.py
├── README.md
├── jobfinder.db
├── app_logs/
├── job_matcher_app/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── services.py
│   └── ui.py
├── resume_reader.py
├── scraper.py
```

## Tech stack

- Python
- Streamlit
- SentenceTransformers
- PyMuPDF
- pandas
- scikit-learn
- JobSpy
- SQLite

## Setup

1. Create and activate a Python environment.
2. Install dependencies:

```bash
pip install streamlit pandas pymupdf sentence-transformers scikit-learn jobspy
```

3. Run the app:

```bash
streamlit run matcher.py
```

## How to use

1. Open the app in Streamlit.
2. Upload a PDF resume.
3. Confirm or edit the detected target position.
4. Choose countries, job sources, and days lookback.
5. Click **Find Current Jobs**.
6. Review the top 5 matches and the full listings table.
7. Open **History & Data Quality** to see saved resumes, search history, and checks.

## Data storage

The app creates a local SQLite database named `jobfinder.db`.
It stores:

- resumes
- search runs
- data-quality checks

## Notes

- JobSpy didn't include **Tunisia**, Package Code has been modded to included 
- Job availability depends on what JobSpy currently supports for each source and country.
- Public scraping results can vary over time.
- For best results, use a resume PDF with readable text, not a scanned image.

## Why this project is useful

This project demonstrates:

- document ingestion
- text extraction
- semantic matching
- data pipeline thinking
- monitoring and quality checks
- local persistence
- modular application design


## License

No license has been added yet.
