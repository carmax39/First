import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import re
import os
import html as html_mod
from collections import defaultdict

# ─────────────────────────────────────────────
# UI/UX Consultant Design System (Columbia Blue Palette)
# ─────────────────────────────────────────────
COL = {
    "navy": "#002B5B",
    "blue": "#1B6CB0",
    "columbia": "#9BCBEB",
    "columbia_soft": "#C4E0F3",
    "ice": "#F2F8FC",
    "white": "#FFFFFF",
    "slate": "#3D5A73",
    "success": "#2E8B6A",
    "warn": "#D47B2F",
    "danger": "#C04545",
}

st.set_page_config(page_title="Columbia Course Directory", page_icon="🦁", layout="wide")

# ─────────────────────────────────────────────
# Enhanced CSS Overhaul
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="st-"] {{ font-family: 'Inter', sans-serif; }}
    
    .stApp {{ background-color: {COL['ice']}; }}

    /* Course Card Container */
    .course-card {{
        background: {COL['white']};
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        border: 1px solid #E1E8ED;
        box-shadow: 0 4px 12px rgba(0, 43, 91, 0.05);
    }}

    /* Typography */
    .course-title {{ font-size: 1.6rem; font-weight: 700; color: {COL['navy']}; margin-bottom: 4px; }}
    .instructor-text {{ color: {COL['slate']}; font-weight: 500; font-size: 1rem; }}
    
    /* Metrics */
    .metric-box {{ text-align: center; padding: 10px; background: {COL['ice']}; border-radius: 12px; }}
    .metric-value {{ font-size: 1.8rem; font-weight: 800; color: {COL['blue']}; }}
    .metric-label {{ font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: {COL['slate']}; }}

    /* Separate Comment Bubbles */
    .comment-card {{
        background: #F8FAFC;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid {COL['columbia']};
    }}
    .date-badge {{
        display: inline-block;
        background: {COL['columbia_soft']};
        color: {COL['navy']};
        font-size: 0.7rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        margin-bottom: 8px;
        text-transform: uppercase;
    }}
    .comment-body {{ font-size: 0.9rem; color: #1E293B; line-height: 1.6; }}

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Data Engineering Logic
# ─────────────────────────────────────────────
def _safe_json(val):
    if pd.isna(val) or val == "": return {}
    try: return json.loads(val)
    except: return {}

def extract_semester(course_code):
    m = re.search(r"_(\d{4})_(\d)", str(course_code))
    if m:
        year = m.group(1)
        term = {"1": "Spring", "2": "Summer", "3": "Fall"}.get(m.group(2), "Unknown")
        return f"{term} {year}"
    return "N/A"

@st.cache_data
def load_and_unify(path="eval_database.csv"):
    if not os.path.exists(path): return []
    
    df = pd.read_csv(path)
    df["course_title"] = df["course_title"].fillna("Untitled Course").astype(str)
    
    groups = defaultdict(lambda: {
        "titles": set(), "instructors": set(), "codes": set(), 
        "ratings_dist": defaultdict(int), "workload_dist": defaultdict(int),
        "comments": [], "total_votes": 0
    })

    for _, row in df.iterrows():
        title = row["course_title"]
        sem = extract_semester(row["course_code"])
        
        groups[title]["instructors"].add(row["instructor"])
        groups[title]["codes"].add(row["course_code"])
        
        # Aggregate Ratings
        dist = _safe_json(row["overall_distribution"])
        for k, v in dist.items():
            if isinstance(v, dict):
                groups[title]["ratings_dist"][k] += v.get("count", 0)
                groups[title]["total_votes"] += v.get("count", 0)

        # Aggregate Workload
        wl_dist = _safe_json(row["workload_distribution"])
        for k, v in wl_dist.items():
            if isinstance(v, dict):
                groups[title]["workload_dist"][k] += v.get("count", 0)

        # Process Comments
        revs = _safe_json(row["reviews"])
        if isinstance(revs, list):
            for r in revs:
                groups[title]["comments"].append({"text": r, "date": sem})

    return dict(groups)

# ─────────────────────────────────────────────
# Simplified Chart Engine
# ─────────────────────────────────────────────
def build_simple_bar(data_dict, title, color):
    labels = list(data_dict.keys())
    values = list(data_dict.values())
    
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=color,
        text=values, textposition='auto',
    ))
    fig.update_layout(
        height=250, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False, title=dict(text=title, font=dict(size=14, color=COL['slate'])),
        xaxis=dict(showgrid=False), yaxis=dict(visible=False)
    )
    return fig

# ─────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────
def main():
    st.markdown(f"<h1 style='color:{COL['navy']};'>Columbia Course Directory</h1>", unsafe_allow_html=True)
    
    data = load_and_unify()
    if not data:
        st.info("No data found. Please run your downloader and extractor scripts.")
        return

    search = st.text_input("🔍 Search courses, professors, or departments...", "").lower()

    for title, info in data.items():
        if search and search not in title.lower() and search not in str(info['instructors']).lower():
            continue

        # Render Course Card
        st.markdown(f"""
        <div class="course-card">
            <div class="course-title">{html_mod.escape(title)}</div>
            <div class="instructor-text">Prof. {', '.join(filter(None, info['instructors']))}</div>
            <hr style="margin: 20px 0; border: 0; border-top: 1px solid #eee;">
        </div>
        """, unsafe_allow_html=True)

        # Layout for Charts
        col1, col2, col3 = st.columns([1, 2, 2])
        
        with col1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Total Reviews</div>
                <div class="metric-value">{len(info['comments'])}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            if info["ratings_dist"]:
                st.plotly_chart(build_simple_bar(info["ratings_dist"], "Rating Distribution", COL['blue']), use_container_width=True)
        
        with col3:
            if info["workload_dist"]:
                st.plotly_chart(build_simple_bar(info["workload_dist"], "Workload Breakdown", COL['slate']), use_container_width=True)

        # Reviews Section
        with st.expander("💬 Read Student Feedback"):
            if not info['comments']:
                st.write("No written reviews available.")
            else:
                for c in info['comments']:
                    st.markdown(f"""
                    <div class="comment-card">
                        <div class="date-badge">{c['date']}</div>
                        <div class="comment-body">{html_mod.escape(c['text'])}</div>
                    </div>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()