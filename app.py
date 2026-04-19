"""
Columbia Course Evaluation Directory
=====================================
Clean academic directory. Reads eval_database.csv, groups by
(course_title, instructor), sums distributions, provides
filterable browsing with pagination.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import re
import math
import html as html_mod
from collections import defaultdict

st.set_page_config(
    page_title="Course Evaluations",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Palette ───
C = dict(
    bg="#FAFBFD", card="#FFFFFF", navy="#0F2B46", navy2="#1B3A5C",
    blue="#3B7DD8", sky="#6FA8DC", ice="#E9F0F8", ice2="#F0F5FA",
    text="#1C2A3A", text2="#4A5D72", text3="#8494A7",
    border="#DDE4EC", border2="#EBF0F5",
    green="#2D7D5F", amber="#C47E24", red="#B84040",
    warm="#F8F6F3",
)

# ─── CSS ───
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap');

html, body, [class*="st-"] {{
    font-family: 'Inter', -apple-system, sans-serif;
}}

.stApp {{ background: {C["bg"]}; }}

header[data-testid="stHeader"] {{
    background: rgba(250,251,253,0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid {C["border2"]};
}}

#MainMenu, footer {{ visibility: hidden; }}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {{
    background: {C["navy"]};
    padding-top: 1.5rem;
}}
section[data-testid="stSidebar"] * {{
    color: {C["ice"]} !important;
}}
section[data-testid="stSidebar"] input {{
    background: {C["navy2"]} !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #fff !important;
    border-radius: 6px !important;
}}
section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {{
    background: {C["navy2"]};
    border-color: rgba(255,255,255,0.12);
}}
section[data-testid="stSidebar"] label {{
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: {C["text3"]} !important;
    margin-bottom: 2px !important;
}}
section[data-testid="stSidebar"] .stMetric label {{
    color: {C["sky"]} !important;
}}
section[data-testid="stSidebar"] .stMetric [data-testid="stMetricValue"] {{
    color: #fff !important;
    font-family: 'Source Serif 4', Georgia, serif !important;
}}
section[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.08);
    margin: 0.8rem 0;
}}
section[data-testid="stSidebar"] .stSlider label {{
    color: {C["text3"]} !important;
}}

/* ── Page header ── */
.pg-hdr {{
    padding: 1.6rem 0 0.8rem;
}}
.pg-hdr h1 {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.65rem;
    font-weight: 700;
    color: {C["navy"]};
    margin: 0 0 0.15rem;
    letter-spacing: -0.01em;
}}
.pg-hdr p {{
    font-size: 0.85rem;
    color: {C["text3"]};
    margin: 0;
}}

/* ── Card ── */
.card {{
    background: {C["card"]};
    border: 1px solid {C["border"]};
    border-radius: 10px;
    padding: 1.4rem 1.6rem 1.2rem;
    margin-bottom: 1rem;
    transition: border-color 0.15s;
}}
.card:hover {{
    border-color: {C["sky"]};
}}

.card-dept {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: {C["navy"]};
    background: {C["ice"]};
    padding: 2px 6px;
    border-radius: 3px;
    display: inline-block;
    margin: 0 3px 4px 0;
    letter-spacing: 0.02em;
}}
.card-title {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: {C["text"]};
    line-height: 1.3;
    margin: 2px 0 1px;
}}
.card-meta {{
    font-size: 0.8rem;
    color: {C["text2"]};
    margin-bottom: 0.15rem;
}}
.card-sem {{
    font-size: 0.72rem;
    color: {C["text3"]};
}}

/* ── Score pill ── */
.score {{
    text-align: right;
}}
.score-num {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}}
.score-lbl {{
    font-size: 0.62rem;
    color: {C["text3"]};
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 1px;
}}

/* ── Stat row ── */
.stat {{
    background: {C["ice2"]};
    border-radius: 8px;
    padding: 0.6rem 0.7rem;
    text-align: center;
}}
.stat-v {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.3rem;
    font-weight: 600;
    line-height: 1.1;
}}
.stat-l {{
    font-size: 0.6rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {C["text3"]};
    margin-top: 1px;
}}

/* ── Section label ── */
.sec {{
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: {C["text3"]};
    margin: 1rem 0 0.35rem;
    padding-bottom: 0.2rem;
    border-bottom: 1px solid {C["border2"]};
}}

/* ── Color classes ── */
.c-hi {{ color: {C["green"]}; }}
.c-md {{ color: {C["blue"]}; }}
.c-lo {{ color: {C["amber"]}; }}
.c-bad {{ color: {C["red"]}; }}

/* ── Feed ── */
.feed {{
    max-height: 340px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: {C["border"]} transparent;
}}
.feed::-webkit-scrollbar {{ width: 4px; }}
.feed::-webkit-scrollbar-thumb {{ background: {C["border"]}; border-radius: 2px; }}

.rv {{
    background: {C["ice2"]};
    border-radius: 7px;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.35rem;
    font-size: 0.82rem;
    line-height: 1.55;
    color: {C["text"]};
}}
.rv-d {{
    font-size: 0.62rem;
    font-weight: 600;
    color: {C["blue"]};
    margin-bottom: 2px;
}}

/* ── Hours ── */
.hrs {{
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    gap: 5px;
    padding: 4px 0;
    scrollbar-width: thin;
    scrollbar-color: {C["border"]} transparent;
}}
.hrs::-webkit-scrollbar {{ height: 3px; }}
.hrs::-webkit-scrollbar-thumb {{ background: {C["border"]}; border-radius: 2px; }}
.hr-c {{
    flex-shrink: 0;
    background: {C["ice"]};
    border-radius: 14px;
    padding: 3px 10px;
    font-size: 0.72rem;
    color: {C["navy"]};
    white-space: nowrap;
}}
.hr-s {{ font-size: 0.58rem; color: {C["text3"]}; margin-left: 3px; }}

/* ── Source ── */
.src {{
    margin-top: 0.6rem;
    padding-top: 0.4rem;
    border-top: 1px solid {C["border2"]};
}}
.src-f {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.55rem;
    color: {C["text3"]};
    word-break: break-all;
    line-height: 1.3;
}}

/* ── Empty ── */
.empty {{
    text-align: center;
    padding: 1.2rem;
    color: {C["text3"]};
    font-size: 0.82rem;
    font-style: italic;
}}

/* ── Landing ── */
.land {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 65vh;
    text-align: center;
}}
.land-mark {{
    width: 48px; height: 48px;
    border-radius: 12px;
    background: {C["navy"]};
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 0.8rem;
}}
.land-mark span {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: {C["sky"]};
}}
.land h1 {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: {C["navy"]};
    margin: 0 0 0.25rem;
}}
.land p {{
    font-size: 0.88rem;
    color: {C["text2"]};
    margin: 0 0 1.2rem;
    max-width: 380px;
}}
.land-row {{
    display: flex;
    gap: 2rem;
    margin-top: 1.2rem;
}}
.land-n {{
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: {C["navy"]};
    line-height: 1;
}}
.land-l {{
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {C["text3"]};
    margin-top: 2px;
}}

/* ── Pagination ── */
.pag {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem 0;
    font-size: 0.82rem;
    color: {C["text2"]};
}}

/* ── Kill expanders ── */
[data-testid="stExpander"] {{ display: none !important; }}

</style>
""", unsafe_allow_html=True)

# ─── Session ───
for k, v in [("page", "landing"), ("q", ""), ("pg", 1)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Data ───
TERM_MAP = {"1": "Spring", "2": "Summer", "3": "Fall"}
R_CANON = {"Excellent": "Excellent", "Very Good": "Very Good",
           "Very good": "Very Good", "Good": "Good",
           "Fair": "Fair", "Poor": "Poor"}
R_ORD = ["Excellent", "Very Good", "Good", "Fair", "Poor"]
R_W = {"Excellent": 5, "Very Good": 4, "Good": 3, "Fair": 2, "Poor": 1}
WL_K = ["Much heavier workload", "Heavier workload", "Similar workload",
        "Lighter workload", "Much lighter workload"]
WL_S = ["Much heavier", "Heavier", "Similar", "Lighter", "Much lighter"]
WL_W = {k: i + 1 for i, k in enumerate(WL_K)}
POISON = ["Response Option", "Weight Frequency", "Mean Excellent",
          "STD Median", "Percent Responses", "Response Rate"]
CODE_RE = re.compile(r"^[A-Z]{2,10}UN?\d{3,5}[_\d\-\s]*$")


def _j(v, c=""):
    if pd.isna(v) or v == "":
        return {} if "dist" in c else []
    try:
        return json.loads(v)
    except Exception:
        return {} if isinstance(v, str) and v.strip().startswith("{") else []


def _sem(code, src):
    for s in [code, src]:
        m = re.search(r"_(\d{3})_(\d{4})_(\d)", str(s))
        if m:
            return f"{TERM_MAP.get(m.group(3), '?')} {m.group(2)}"
    return "Unknown"


def _dept(code):
    m = re.match(r"^([A-Z]+)", str(code))
    return m.group(1) if m else "OTHER"


def _clean(t):
    t = str(t).strip()
    if not t:
        return ""
    for p in POISON:
        i = t.find(p)
        if i != -1:
            t = t[:i].strip()
    rm = re.search(r"\b\d{1,3}/\d{2,4}\b", t)
    if rm:
        b = t[:rm.start()].rstrip()
        t = b if len(b) > 10 else ""
    if len(t) < 20 or CODE_RE.match(t):
        return ""
    return t


@st.cache_data
def load(path="eval_database.csv"):
    df = pd.read_csv(path)
    for c in ["overall_distribution", "workload_distribution",
              "reviews", "hours_per_week_responses"]:
        df[c] = df[c].apply(lambda x, cn=c: _j(x, cn))
    for c in ["overall_mean", "overall_std", "overall_median", "workload_mean"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["course_title"] = df["course_title"].fillna("Unknown Course")
    df["instructor"] = df["instructor"].fillna("Unknown")
    df["semester"] = df.apply(
        lambda r: _sem(str(r.get("course_code", "")),
                       str(r.get("source_file", ""))), axis=1)

    grp = defaultdict(list)
    for _, r in df.iterrows():
        grp[(r["course_title"].strip(), r["instructor"].strip())].append(r)

    out = []
    for (title, inst), rows in grp.items():
        rat = {k: 0 for k in R_ORD}
        for r in rows:
            d = r["overall_distribution"]
            if isinstance(d, dict):
                for rk, info in d.items():
                    cn = R_CANON.get(rk)
                    if cn and isinstance(info, dict):
                        rat[cn] += info.get("count", 0)
        rt = sum(rat.values())
        rm = round(sum(rat[k] * R_W[k] for k in R_ORD) / rt, 2) if rt > 0 else None

        wl = {k: 0 for k in WL_K}
        for r in rows:
            d = r["workload_distribution"]
            if isinstance(d, dict):
                for k in WL_K:
                    if k in d and isinstance(d[k], dict):
                        wl[k] += d[k].get("count", 0)
        wt = sum(wl.values())
        wm = round(sum(wl[k] * WL_W[k] for k in WL_K) / wt, 2) if wt > 0 else None

        coms = []
        for r in rows:
            s = r["semester"]
            for t in (r["reviews"] if isinstance(r["reviews"], list) else []):
                cl = _clean(t)
                if cl:
                    coms.append({"t": cl, "s": s, "l": len(cl)})

        hrs = []
        for r in rows:
            s = r["semester"]
            for h in (r["hours_per_week_responses"]
                      if isinstance(r["hours_per_week_responses"], list) else []):
                v = str(h).strip()
                if v:
                    hrs.append({"t": v, "s": s})

        codes = sorted(set(str(r["course_code"]).strip() for r in rows
                           if pd.notna(r.get("course_code"))))
        srcs = [str(r["source_file"]) for r in rows if pd.notna(r.get("source_file"))]
        sems = sorted(set(r["semester"] for r in rows))
        dept = _dept(codes[0]) if codes else "OTHER"

        out.append(dict(
            title=title, inst=inst, codes=codes, sems=sems, srcs=srcs,
            dept=dept, rat=rat, rt=rt, rm=rm, wl=wl, wt=wt, wm=wm,
            coms=coms, hrs=hrs,
        ))
    return out


# ─── Helpers ───
def _rc(v):
    if v is None: return "c-lo"
    if v >= 4.5: return "c-hi"
    if v >= 3.5: return "c-md"
    if v >= 2.5: return "c-lo"
    return "c-bad"

def _wl(v):
    if v is None: return "N/A"
    if v >= 4.0: return "Light"
    if v >= 3.0: return "Average"
    if v >= 2.0: return "Heavy"
    return "Very Heavy"

def _wc(v):
    l = _wl(v)
    return {
        "Light": C["green"], "Average": C["blue"],
        "Heavy": C["amber"], "Very Heavy": C["red"], "N/A": C["text3"]
    }[l]

def esc(t):
    return html_mod.escape(str(t))

def fmt(v):
    return f"{v:.2f}" if v is not None else "\u2014"


# ─── Charts ───
CB = [C["navy"], C["navy2"], C["blue"], C["sky"], "#B8D4EE"]
CW = [C["red"], C["amber"], C["blue"], C["green"], "#1A5C44"]

def _bar(labels, counts, colors, title):
    fig = go.Figure(go.Bar(
        y=labels, x=counts, orientation="h",
        marker_color=colors, marker_line_width=0,
        text=counts, textposition="outside",
        textfont=dict(size=11, family="Inter", color=C["text2"]),
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        height=210, margin=dict(l=100, r=30, t=28, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color=C["text2"]),
        xaxis=dict(visible=False),
        yaxis=dict(tickfont=dict(size=10.5, color=C["text2"]),
                   showgrid=False, autorange="reversed"),
        title=dict(text=title, font=dict(size=11, color=C["text3"]),
                   x=0, xanchor="left"),
        bargap=0.42,
    )
    return fig

def ch_rat(d):
    return _bar(R_ORD, [d.get(k, 0) for k in R_ORD], CB, "Rating Distribution")

def ch_wl(d):
    return _bar(WL_S, [d.get(k, 0) for k in WL_K], CW, "Workload Comparison")


# ─── Card ───
PER_PAGE = 12

def render(c, idx):
    rc = _rc(c["rm"])
    ms = fmt(c["rm"])
    ws = fmt(c["wm"])
    wl = _wl(c["wm"])

    st.markdown('<div class="card">', unsafe_allow_html=True)

    # Header
    L, R = st.columns([4, 1])
    with L:
        tags = "".join(f'<span class="card-dept">{esc(x)}</span>' for x in c["codes"])
        st.markdown(tags, unsafe_allow_html=True)
        st.markdown(f'<div class="card-title">{esc(c["title"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-meta">{esc(c["inst"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-sem">{esc(" / ".join(c["sems"]))}</div>', unsafe_allow_html=True)
    with R:
        st.markdown(
            f'<div class="score">'
            f'<div class="score-num {rc}">{ms}</div>'
            f'<div class="score-lbl">of 5.00</div></div>',
            unsafe_allow_html=True)

    # Stats
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f'<div class="stat"><div class="stat-v {rc}">{ms}</div><div class="stat-l">Rating ({c["rt"]} votes)</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="stat"><div class="stat-v" style="color:{_wc(c["wm"])}">{ws}</div><div class="stat-l">Workload ({wl})</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="stat"><div class="stat-v" style="color:{C["blue"]}">{len(c["coms"])}</div><div class="stat-l">Reviews</div></div>', unsafe_allow_html=True)

    # Charts
    if c["rt"] > 0 or c["wt"] > 0:
        st.markdown('<div class="sec">Distributions</div>', unsafe_allow_html=True)
        cl, cr = st.columns(2)
        if c["rt"] > 0:
            with cl:
                st.plotly_chart(ch_rat(c["rat"]), use_container_width=True, key=f"r_{idx}")
        if c["wt"] > 0:
            with cr:
                st.plotly_chart(ch_wl(c["wl"]), use_container_width=True, key=f"w_{idx}")

    # Reviews
    st.markdown('<div class="sec">Student Reviews</div>', unsafe_allow_html=True)
    if c["coms"]:
        fc1, fc2 = st.columns([1, 2])
        with fc1:
            so = st.selectbox("Sort", ["Newest", "Longest", "Shortest"],
                              key=f"so_{idx}", label_visibility="collapsed")
        with fc2:
            kw = st.text_input("Filter", placeholder="Search reviews...",
                               key=f"kw_{idx}", label_visibility="collapsed")

        cl = c["coms"]
        if kw.strip():
            kl = kw.strip().lower()
            cl = [x for x in cl if kl in x["t"].lower()]
        if so == "Longest":
            cl = sorted(cl, key=lambda x: x["l"], reverse=True)
        elif so == "Shortest":
            cl = sorted(cl, key=lambda x: x["l"])
        else:
            cl = sorted(cl, key=lambda x: x["s"], reverse=True)

        if cl:
            if kw.strip():
                st.caption(f"{len(cl)} of {len(c['coms'])} reviews")
            buf = ['<div class="feed">']
            for rv in cl:
                buf.append(f'<div class="rv"><div class="rv-d">{esc(rv["s"])}</div>{esc(rv["t"])}</div>')
            buf.append('</div>')
            st.markdown("".join(buf), unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No reviews match your filter.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty">No written reviews available.</div>', unsafe_allow_html=True)

    # Hours
    if c["hrs"]:
        st.markdown('<div class="sec">Weekly Hours</div>', unsafe_allow_html=True)
        ch = ['<div class="hrs">']
        for h in c["hrs"]:
            ch.append(f'<span class="hr-c">{esc(h["t"])}<span class="hr-s">{esc(h["s"])}</span></span>')
        ch.append('</div>')
        st.markdown("".join(ch), unsafe_allow_html=True)

    # Sources
    if c["srcs"]:
        st.markdown(
            f'<div class="src"><div style="font-size:0.6rem;font-weight:600;color:{C["text3"]};'
            f'text-transform:uppercase;letter-spacing:0.04em;margin-bottom:2px;">'
            f'Sources ({len(c["srcs"])})</div>'
            + "".join(f'<div class="src-f">{esc(s)}</div>' for s in c["srcs"])
            + '</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ─── Landing ───
def landing(courses):
    insts = set(c["inst"] for c in courses)
    ms = [c["rm"] for c in courses if c["rm"] is not None]
    avg = sum(ms) / len(ms) if ms else None

    st.markdown('<div class="land">', unsafe_allow_html=True)
    st.markdown('<div class="land-mark"><span>C</span></div>', unsafe_allow_html=True)
    st.markdown('<h1>Course Evaluations</h1>', unsafe_allow_html=True)
    st.markdown(f'<p>Browse {len(courses)} courses by title, instructor, or department.</p>', unsafe_allow_html=True)

    _, ctr, _ = st.columns([1.2, 2, 1.2])
    with ctr:
        with st.form("sf", clear_on_submit=False, border=False):
            q = st.text_input("Search", placeholder="e.g. Game of Thrones, Dabashi, ECON ...",
                              label_visibility="collapsed")
            b1, b2 = st.columns(2)
            with b1:
                if st.form_submit_button("Search", use_container_width=True):
                    st.session_state.q = q.strip()
                    st.session_state.page = "browse"
                    st.session_state.pg = 1
                    st.rerun()
            with b2:
                if st.form_submit_button("Browse All", use_container_width=True):
                    st.session_state.q = ""
                    st.session_state.page = "browse"
                    st.session_state.pg = 1
                    st.rerun()

    av = fmt(avg) if avg else "\u2014"
    st.markdown(
        f'<div class="land-row">'
        f'<div><div class="land-n">{len(courses)}</div><div class="land-l">Courses</div></div>'
        f'<div><div class="land-n">{len(insts)}</div><div class="land-l">Instructors</div></div>'
        f'<div><div class="land-n">{av}</div><div class="land-l">Avg Rating</div></div>'
        f'</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ─── Browse ───
def browse(courses):
    depts = sorted(set(c["dept"] for c in courses))
    insts = sorted(set(c["inst"] for c in courses))

    with st.sidebar:
        st.markdown(f'<div style="font-family:Source Serif 4,Georgia,serif;font-size:1.1rem;font-weight:700;color:#fff;margin-bottom:0.3rem;">Course Directory</div>', unsafe_allow_html=True)
        st.markdown("---")

        if st.button("Home", use_container_width=True):
            st.session_state.page = "landing"
            st.session_state.q = ""
            st.session_state.pg = 1
            st.rerun()

        q = st.text_input("Search", value=st.session_state.q,
                          placeholder="Title, instructor, code...", key="sq")
        st.session_state.q = q.strip()

        st.markdown("---")
        sort_by = st.selectbox("Sort", [
            "Highest Rating", "Lowest Rating",
            "Lightest Workload", "Heaviest Workload",
            "Most Reviews", "Title A-Z", "Instructor A-Z"])

        dept_f = st.selectbox("Department", ["All"] + depts)
        inst_f = st.selectbox("Instructor", ["All"] + insts)
        rat_f = st.select_slider("Min Rating", options=[0, 1, 2, 3, 4, 5], value=0)
        wl_f = st.selectbox("Workload", ["Any", "Light", "Average", "Heavy"])

        st.markdown("---")
        st.metric("Courses", len(courses))
        ms = [c["rm"] for c in courses if c["rm"] is not None]
        if ms:
            st.metric("Avg Rating", f"{sum(ms)/len(ms):.2f}")

    # Filter
    f = list(courses)
    if st.session_state.q:
        ql = st.session_state.q.lower()
        f = [c for c in f
             if ql in c["title"].lower()
             or any(ql in x.lower() for x in c["codes"])
             or ql in c["inst"].lower()
             or ql in c["dept"].lower()]
    if dept_f != "All":
        f = [c for c in f if c["dept"] == dept_f]
    if inst_f != "All":
        f = [c for c in f if c["inst"] == inst_f]
    if rat_f > 0:
        f = [c for c in f if c["rm"] is not None and c["rm"] >= rat_f]
    if wl_f != "Any":
        f = [c for c in f if _wl(c["wm"]) == wl_f]

    # Sort
    def sk(c, fld):
        v = c.get(fld)
        return v if v is not None else -999

    sm = {
        "Highest Rating": lambda: f.sort(key=lambda c: sk(c, "rm"), reverse=True),
        "Lowest Rating": lambda: f.sort(key=lambda c: sk(c, "rm")),
        "Lightest Workload": lambda: f.sort(key=lambda c: sk(c, "wm"), reverse=True),
        "Heaviest Workload": lambda: f.sort(key=lambda c: sk(c, "wm")),
        "Most Reviews": lambda: f.sort(key=lambda c: len(c["coms"]), reverse=True),
        "Title A-Z": lambda: f.sort(key=lambda c: c["title"].lower()),
        "Instructor A-Z": lambda: f.sort(key=lambda c: c["inst"].lower()),
    }
    sm.get(sort_by, lambda: None)()

    # Header
    note = f'for "{esc(st.session_state.q)}"' if st.session_state.q else ""
    st.markdown(
        f'<div class="pg-hdr">'
        f'<h1>Course Evaluations</h1>'
        f'<p>{len(f)} courses {note}</p></div>',
        unsafe_allow_html=True)

    if not f:
        st.markdown('<div class="empty">No courses match your filters.</div>',
                    unsafe_allow_html=True)
        return

    # Pagination
    total_pages = max(1, math.ceil(len(f) / PER_PAGE))
    if st.session_state.pg > total_pages:
        st.session_state.pg = total_pages
    page = st.session_state.pg

    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_items = f[start:end]

    for i, c in enumerate(page_items):
        render(c, start + i)

    # Page controls
    if total_pages > 1:
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc2:
            nc1, nc2, nc3 = st.columns([1, 1, 1])
            with nc1:
                if page > 1:
                    if st.button("Previous", use_container_width=True, key="prev"):
                        st.session_state.pg = page - 1
                        st.rerun()
            with nc2:
                st.markdown(
                    f'<div style="text-align:center;padding:0.5rem;'
                    f'font-size:0.82rem;color:{C["text2"]};">'
                    f'Page {page} of {total_pages}</div>',
                    unsafe_allow_html=True)
            with nc3:
                if page < total_pages:
                    if st.button("Next", use_container_width=True, key="next"):
                        st.session_state.pg = page + 1
                        st.rerun()


# ─── Router ───
def main():
    courses = load()
    if st.session_state.page == "landing":
        landing(courses)
    else:
        browse(courses)


if __name__ == "__main__":
    main()