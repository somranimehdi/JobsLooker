import logging

import streamlit as st
from sentence_transformers import SentenceTransformer

from .config import APP_LAYOUT, APP_TITLE, LOG_DIR, LOG_FILE, MODEL_NAME
from .database import DatabaseManager
from .services import DataQualityService, JobSearchService, ResumeAnalyzer
from .ui import HistoryPage, JobsLookerPage, PageContext


class JobMatcherApp:
    def __init__(self):
        LOG_DIR.mkdir(exist_ok=True)
        self.logger = logging.getLogger("job_matcher")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        self.database = DatabaseManager()
        self.database.initialize()
        self.model = SentenceTransformer(MODEL_NAME)
        self.analyzer = ResumeAnalyzer(self.model)
        self.search_service = JobSearchService()
        self.quality_service = DataQualityService()
        self.context = PageContext(
            analyzer=self.analyzer,
            search_service=self.search_service,
            quality_service=self.quality_service,
            database=self.database,
            logger=self.logger,
            model=self.model,
        )
        self.pages = {
            "Jobs Looker": JobsLookerPage(self.context),
            "History & Data Quality": HistoryPage(self.context),
        }

    def _render_nav(self):
        st.sidebar.markdown("### Navigate")
        if "page_selector" not in st.session_state:
            st.session_state.page_selector = "Jobs Looker"

        current_page = st.session_state.page_selector
        for page_name in self.pages.keys():
            is_selected = page_name == current_page
            button_label = f"{'👉 ' if is_selected else ''}{page_name}"
            if st.sidebar.button(button_label, key=f"nav_{page_name}", use_container_width=True, type="primary" if is_selected else "secondary"):
                st.session_state.page_selector = page_name
                st.rerun()

        st.sidebar.divider()
        st.sidebar.caption("Tip: use 'Check again' from History to load a saved resume.")

    def run(self):
        st.set_page_config(page_title=APP_TITLE, layout=APP_LAYOUT)
        st.title("🌐 AI Resume-to-Jobs Matcher")
        st.write("Upload one resume at a time. History and data quality are in a separate page.")
        self._render_nav()

        page_name = st.session_state.page_selector
        page = self.pages.get(page_name, self.pages["Jobs Looker"])
        page.render()
