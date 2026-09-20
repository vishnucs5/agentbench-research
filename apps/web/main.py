from __future__ import annotations

import requests
import streamlit as st
from packages.domain.config import get_settings

settings = get_settings()

st.set_page_config(page_title="AgentBench-Research", page_icon="🔬", layout="wide")

st.title("🔬 AgentBench-Research")
st.caption("Evidence-grounded autonomous research-paper analysis agent")

with st.sidebar:
    st.header("Configuration")
    st.write(f"Environment: {settings.app_env}")
    st.write(f"Model Provider: {settings.default_model_provider}")
    st.write(f"Model: {settings.ollama_model if settings.default_model_provider == 'ollama' else settings.openrouter_model}")

    if st.button("Check API Health"):
        try:
            resp = requests.get(f"{settings.database_url.replace('postgresql+asyncpg://', 'http://').split('@')[1].split('/')[0]}/healthz", timeout=5)
            if resp.status_code == 200:
                st.success("API Healthy")
            else:
                st.error(f"API Error: {resp.status_code}")
        except Exception as e:
            st.error(f"Cannot reach API: {e}")

tab1, tab2, tab3, tab4 = st.tabs(["Projects", "Papers", "Runs", "Evaluation"])

with tab1:
    st.header("Projects")
    st.info("Project management UI coming soon")

with tab2:
    st.header("Papers")
    st.info("Paper upload and library UI coming soon")

with tab3:
    st.header("Research Runs")
    st.info("Run management and trace replay UI coming soon")

with tab4:
    st.header("Evaluation Dashboard")
    st.info("Benchmark results and metrics UI coming soon")

st.divider()
st.caption("AgentBench-Research v0.1.0 | Built with FastAPI, Streamlit, and ❤️")
