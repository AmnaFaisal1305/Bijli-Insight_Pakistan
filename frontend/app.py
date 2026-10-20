"""
Location: frontend/app.py
Purpose: Lightweight Streamlit monitoring dashboard for Hugging Face Spaces.
         Renders the 3 mandatory cards: Data Freshness, Quality Status, and Last Run Status.
"""

from pathlib import Path
import json
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bijli-Insight Monitor", page_icon="⚡", layout="wide")

st.title("⚡ Bijli-Insight Pakistan: Operational Monitor")
st.markdown("*Real-Time Pipeline Health, Data Quality Audit & Quantile Forecasting*")

STATUS_FILE = Path("data/pipeline_status.json")
QUALITY_LOG_FILE = Path("data/quality_log.json")


def load_status_payload() -> dict:
    """Reads pipeline_status.json or returns default fallback if uninitialized."""
    # ALGORITHM:
    # if STATUS_FILE.exists():
    #     return json.loads(STATUS_FILE.read_text())
    # return {"status": "INITIALIZING", "data_freshness_minutes": 0, "last_run_utc": "N/A"}
    raise NotImplementedError


def load_quality_counts() -> dict:
    """Aggregates counts of FIX, FILL, and FLAG actions from quality_log.json."""
    # ALGORITHM:
    # counts = {"FIX": 0, "FILL": 0, "FLAG": 0}
    # if QUALITY_LOG_FILE.exists():
    #     logs = json.loads(QUALITY_LOG_FILE.read_text())
    #     for item in logs: counts[item["action_taken"]] += item["affected_rows_count"]
    # return counts
    raise NotImplementedError


# RENDER 3 STATUS CARDS
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📡 Card 1: Data Freshness")
    # UI LOGIC:
    # 1. Display elapsed minutes since last fetch
    # 2. If minutes < 65: st.success("Status: FRESH (Within 1h window)")
    # 3. Else: st.warning("Status: STALE (> 65 mins ago)")

with col2:
    st.subheader("🛡️ Card 2: Quality Status")
    # UI LOGIC:
    # Display metrics: st.metric("FIX Actions", x), st.metric("FILL Actions", y), st.metric("FLAG Actions", z)

with col3:
    st.subheader("⏱️ Card 3: Last Run & Model vs Baseline")
    # UI LOGIC:
    # 1. Display last run completion timestamp
    # 2. Display Model MAE vs. Declared Persistence Baseline MAE
    # 3. Show LightGBM improvement percentage