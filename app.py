"""
EDQI Engine — Single-file Streamlit App
ESG Disclosure Quality Index · BRR (ERA 1, FY2012-2021) + BRSR (ERA 2, FY2022-2025)

Run:
    streamlit run app.py
"""

from __future__ import annotations

import io
import json
import math
import re

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# INDICATORS
# ══════════════════════════════════════════════════════════════════════════════

ERA1_IND = [
    # Environmental (9)
    {"id": "E1",  "pillar": "E", "era": 1, "name": "GHG Scope 1+2",           "unit": "tCO2e",      "inv": True},
    {"id": "E2",  "pillar": "E", "era": 1, "name": "GHG Intensity",            "unit": "tCO2e/Rcr",  "inv": True},
    {"id": "E3",  "pillar": "E", "era": 1, "name": "Energy Consumption",       "unit": "GJ or kWh",  "inv": True},
    {"id": "E4",  "pillar": "E", "era": 1, "name": "Energy Intensity",         "unit": "GJ/Rcr",     "inv": True},
    {"id": "E5",  "pillar": "E", "era": 1, "name": "Renewable Energy",         "unit": "%",          "inv": False},
    {"id": "E6",  "pillar": "E", "era": 1, "name": "Water Withdrawal",         "unit": "kL/yr",      "inv": True},
    {"id": "E7",  "pillar": "E", "era": 1, "name": "Water Intensity",          "unit": "kL/Rcr",     "inv": True},
    {"id": "E8",  "pillar": "E", "era": 1, "name": "Waste Generated",          "unit": "MT/yr",      "inv": True},
    {"id": "E9",  "pillar": "E", "era": 1, "name": "Waste Recycled",           "unit": "%",          "inv": False},
    # Social (10)
    {"id": "S1",  "pillar": "S", "era": 1, "name": "Permanent Employees",      "unit": "count",      "inv": False},
    {"id": "S2",  "pillar": "S", "era": 1, "name": "Women Employees",          "unit": "%",          "inv": False},
    {"id": "S3",  "pillar": "S", "era": 1, "name": "Training Hours/Employee",  "unit": "hrs/yr",     "inv": False},
    {"id": "S4",  "pillar": "S", "era": 1, "name": "Training Spend",           "unit": "Rs cr",      "inv": False},
    {"id": "S5",  "pillar": "S", "era": 1, "name": "CSR Expenditure",          "unit": "Rs cr",      "inv": False},
    {"id": "S6",  "pillar": "S", "era": 1, "name": "CSR as % of PAT",          "unit": "%",          "inv": False},
    {"id": "S7",  "pillar": "S", "era": 1, "name": "Safety Incidents",         "unit": "count",      "inv": True},
    {"id": "S8",  "pillar": "S", "era": 1, "name": "LTIFR",                    "unit": "per Mmhr",   "inv": True},
    {"id": "S9",  "pillar": "S", "era": 1, "name": "Employee Grievances",      "unit": "count",      "inv": True},
    {"id": "S10", "pillar": "S", "era": 1, "name": "Customer Complaints",      "unit": "count",      "inv": True},
    # Governance (6)
    {"id": "G1",  "pillar": "G", "era": 1, "name": "Board Meetings",           "unit": "count/yr",   "inv": False},
    {"id": "G2",  "pillar": "G", "era": 1, "name": "Independent Directors",    "unit": "%",          "inv": False},
    {"id": "G3",  "pillar": "G", "era": 1, "name": "Women on Board",           "unit": "%",          "inv": False},
    {"id": "G4",  "pillar": "G", "era": 1, "name": "Audit Committee Meetings", "unit": "count/yr",   "inv": False},
    {"id": "G5",  "pillar": "G", "era": 1, "name": "Director Attendance",      "unit": "%",          "inv": False},
    {"id": "G6",  "pillar": "G", "era": 1, "name": "CSR Committee Meetings",   "unit": "count/yr",   "inv": False},
]

ERA2_IND = [
    # Environmental (13)
    {"id": "BE1",  "pillar": "E", "era": 2, "name": "GHG Scope 1",                    "unit": "tCO2e",     "inv": True},
    {"id": "BE2",  "pillar": "E", "era": 2, "name": "GHG Scope 2",                    "unit": "tCO2e",     "inv": True},
    {"id": "BE3",  "pillar": "E", "era": 2, "name": "GHG Intensity",                  "unit": "tCO2e/Rcr", "inv": True},
    {"id": "BE4",  "pillar": "E", "era": 2, "name": "Energy Consumption",             "unit": "GJ",        "inv": True},
    {"id": "BE5",  "pillar": "E", "era": 2, "name": "Renewable Energy",               "unit": "%",         "inv": False},
    {"id": "BE6",  "pillar": "E", "era": 2, "name": "Energy Intensity",               "unit": "GJ/Rcr",    "inv": True},
    {"id": "BE7",  "pillar": "E", "era": 2, "name": "Water Withdrawal",               "unit": "kL",        "inv": True},
    {"id": "BE8",  "pillar": "E", "era": 2, "name": "Water Intensity",                "unit": "kL/Rcr",    "inv": True},
    {"id": "BE9",  "pillar": "E", "era": 2, "name": "Water Recycled",                 "unit": "%",         "inv": False},
    {"id": "BE10", "pillar": "E", "era": 2, "name": "Waste Generated",                "unit": "MT",        "inv": True},
    {"id": "BE11", "pillar": "E", "era": 2, "name": "Hazardous Waste %",              "unit": "%",         "inv": True},
    {"id": "BE12", "pillar": "E", "era": 2, "name": "Waste Recycled %",               "unit": "%",         "inv": False},
    {"id": "BE13", "pillar": "E", "era": 2, "name": "Env Fines Paid",                 "unit": "Rs",        "inv": True},
    # Social (14)
    {"id": "BS1",  "pillar": "S", "era": 2, "name": "Permanent Employees",            "unit": "count",     "inv": False},
    {"id": "BS2",  "pillar": "S", "era": 2, "name": "Women Workforce",                "unit": "%",         "inv": False},
    {"id": "BS3",  "pillar": "S", "era": 2, "name": "Health Insurance Coverage",      "unit": "%",         "inv": False},
    {"id": "BS4",  "pillar": "S", "era": 2, "name": "PF / Retirement Benefit",        "unit": "%",         "inv": False},
    {"id": "BS5",  "pillar": "S", "era": 2, "name": "Return-to-Work Rate",            "unit": "%",         "inv": False},
    {"id": "BS6",  "pillar": "S", "era": 2, "name": "Training Hours/Employee",        "unit": "hrs/yr",    "inv": False},
    {"id": "BS7",  "pillar": "S", "era": 2, "name": "H&S Training %",                 "unit": "%",         "inv": False},
    {"id": "BS8",  "pillar": "S", "era": 2, "name": "Fatalities",                     "unit": "count",     "inv": True},
    {"id": "BS9",  "pillar": "S", "era": 2, "name": "LTIFR",                          "unit": "per Mmhr",  "inv": True},
    {"id": "BS10", "pillar": "S", "era": 2, "name": "POSH Complaints",                "unit": "count",     "inv": True},
    {"id": "BS11", "pillar": "S", "era": 2, "name": "CSR Expenditure",                "unit": "Rs cr",     "inv": False},
    {"id": "BS12", "pillar": "S", "era": 2, "name": "CSR as % of PAT",                "unit": "%",         "inv": False},
    {"id": "BS13", "pillar": "S", "era": 2, "name": "Consumer Complaints",            "unit": "count",     "inv": True},
    {"id": "BS14", "pillar": "S", "era": 2, "name": "Complaint Resolution Rate",      "unit": "%",         "inv": False},
    # Governance (5)
    {"id": "BG1",  "pillar": "G", "era": 2, "name": "Independent Directors",          "unit": "%",         "inv": False},
    {"id": "BG2",  "pillar": "G", "era": 2, "name": "Women Directors",                "unit": "%",         "inv": False},
    {"id": "BG3",  "pillar": "G", "era": 2, "name": "Governance Complaints Resolved", "unit": "%",         "inv": False},
    {"id": "BG4",  "pillar": "G", "era": 2, "name": "Ethics Complaints Filed",        "unit": "count",     "inv": True},
    {"id": "BG5",  "pillar": "G", "era": 2, "name": "BRSR Principles Coverage",       "unit": "%",         "inv": False},
]

ALL_IND = ERA1_IND + ERA2_IND

def get_era(fiscal_year: int) -> int:
    return 2 if fiscal_year >= 2022 else 1

def era_indicators(era: int) -> list:
    return ERA2_IND if era == 2 else ERA1_IND


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

SYS = (
    "You are a precise financial data extraction assistant specialised in Indian corporate "
    "ESG and sustainability reports (BRR / BRSR). Extract ONLY numerical values that are "
    "explicitly stated in the text. Return null for any metric not found. "
    "Always return valid JSON and nothing else — no explanation, no markdown fences."
)

def build_prompt_era1(text: str, year: int) -> str:
    return f"""Extract BRR (Business Responsibility Report) KPIs from the FY{year} annual report excerpt below.
Return a single JSON object with exactly these keys. Use null for any metric not explicitly stated.
Extract NUMBERS only — no units, no text. Percentages on a 0-100 scale.

{{
  "E1":  <GHG Scope 1+2 total emissions tCO2e>,
  "E2":  <GHG intensity tCO2e per crore INR revenue>,
  "E3":  <Total energy consumption GJ or kWh>,
  "E4":  <Energy intensity GJ per crore INR revenue>,
  "E5":  <Renewable energy as % of total energy>,
  "E6":  <Total water withdrawal kilolitres per year>,
  "E7":  <Water intensity kL per crore INR revenue>,
  "E8":  <Total waste generated metric tonnes per year>,
  "E9":  <Waste recycled or reused as % of total waste>,
  "S1":  <Total permanent employees count>,
  "S2":  <Women as % of total employees>,
  "S3":  <Average training hours per employee per year>,
  "S4":  <Total training spend crore INR>,
  "S5":  <CSR expenditure crore INR>,
  "S6":  <CSR spend as % of average net profit or PAT>,
  "S7":  <Number of safety incidents or accidents>,
  "S8":  <Lost Time Injury Frequency Rate per million hours>,
  "S9":  <Number of employee grievances filed>,
  "S10": <Number of customer or consumer complaints>,
  "G1":  <Number of board meetings held during the year>,
  "G2":  <Independent directors as % of total board>,
  "G3":  <Women directors as % of total board>,
  "G4":  <Audit committee meetings held>,
  "G5":  <Average director attendance at board meetings %>,
  "G6":  <CSR committee meetings held>
}}

REPORT EXCERPT — FY{year}:
{text}"""

def build_prompt_era2(text: str, year: int) -> str:
    return f"""Extract BRSR (Business Responsibility and Sustainability Report) KPIs from the FY{year} annual report excerpt below.
Return a single JSON object with exactly these keys. Use null for any metric not explicitly stated.
Extract NUMBERS only — no units, no text. Percentages on a 0-100 scale.

{{
  "BE1":  <GHG Scope 1 direct emissions tCO2e>,
  "BE2":  <GHG Scope 2 indirect emissions tCO2e>,
  "BE3":  <GHG intensity tCO2e per crore INR revenue>,
  "BE4":  <Total energy consumption GJ>,
  "BE5":  <Renewable energy as % of total energy>,
  "BE6":  <Energy intensity GJ per crore INR revenue>,
  "BE7":  <Total water withdrawal kilolitres>,
  "BE8":  <Water intensity kL per crore INR revenue>,
  "BE9":  <Water recycled or reused as % of total water>,
  "BE10": <Total waste generated metric tonnes>,
  "BE11": <Hazardous waste as % of total waste>,
  "BE12": <Waste recycled or recovered as %>,
  "BE13": <Environmental fines or penalties paid INR>,
  "BS1":  <Total permanent employees count>,
  "BS2":  <Women as % of total workforce>,
  "BS3":  <Employees covered by health insurance %>,
  "BS4":  <Employees covered by PF or retirement benefit %>,
  "BS5":  <Return-to-work rate after parental leave %>,
  "BS6":  <Average training hours per employee per year>,
  "BS7":  <Employees trained on health and safety %>,
  "BS8":  <Fatalities at workplace count>,
  "BS9":  <Lost Time Injury Frequency Rate per million hours>,
  "BS10": <POSH complaints received count>,
  "BS11": <CSR expenditure crore INR>,
  "BS12": <CSR as % of average net profit>,
  "BS13": <Consumer complaints received count>,
  "BS14": <Consumer complaint resolution rate %>,
  "BG1":  <Independent directors as % of board>,
  "BG2":  <Women directors as % of board>,
  "BG3":  <Governance or whistleblower complaints resolved %>,
  "BG4":  <Ethics or whistleblower complaints filed count>,
  "BG5":  <BRSR principles with full coverage % of 9 principles>
}}

REPORT EXCERPT — FY{year}:
{text}"""


# ══════════════════════════════════════════════════════════════════════════════
# PDF UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

ESG_KEYWORDS = [
    "greenhouse gas", "ghg", "carbon", "emission", "scope 1", "scope 2",
    "energy consumption", "renewable energy", "water withdrawal", "water intensity",
    "waste generated", "waste recycled", "hazardous waste",
    "csr", "corporate social responsibility",
    "permanent employee", "women employee", "women workforce",
    "training hours", "training spend", "safety incident", "ltifr", "fatality",
    "employee grievance", "customer complaint", "consumer complaint",
    "brsr", "brr", "business responsibility", "esg", "sustainability report",
    "environment", "governance", "independent director", "board meeting",
    "audit committee", "women director", "posh", "return to work",
    "health insurance", "provident fund",
]

def extract_pdf_text(file_bytes: bytes) -> str:
    import pdfplumber
    parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    return "\n".join(parts)

def find_esg_section(full_text: str, window: int = 9000) -> str:
    if len(full_text) <= window:
        return full_text
    text_lower = full_text.lower()
    step = window // 4
    best_score, best_start = -1, 0
    for start in range(0, len(text_lower) - window + 1, step):
        chunk = text_lower[start: start + window]
        score = sum(chunk.count(kw) for kw in ESG_KEYWORDS)
        if score > best_score:
            best_score, best_start = score, start
    return full_text[best_start: best_start + window]

def detect_fiscal_year(filename: str, full_text: str = "") -> int | None:
    def _valid(y): return 2010 <= y <= 2030

    m = re.search(r"20(\d{2})[-_](\d{2})", filename)
    if m:
        century = int("20" + m.group(1)) // 100 * 100
        y = century + int(m.group(2))
        if _valid(y): return y

    m = re.search(r"FY\s?(\d{2,4})", filename, re.IGNORECASE)
    if m:
        raw = int(m.group(1)); y = raw if raw > 100 else 2000 + raw
        if _valid(y): return y

    m = re.search(r"(20\d{2})", filename)
    if m:
        y = int(m.group(1))
        if _valid(y): return y

    if full_text:
        snippet = full_text[:2000]
        m = re.search(r"(?:31st?\s+)?March[,\s]+(\d{4})", snippet, re.IGNORECASE)
        if m:
            y = int(m.group(1))
            if _valid(y): return y
        m = re.search(r"Annual\s+Report\s+(20\d{2})", snippet, re.IGNORECASE)
        if m:
            y = int(m.group(1))
            if _valid(y): return y
    return None


# ══════════════════════════════════════════════════════════════════════════════
# LLM API
# ══════════════════════════════════════════════════════════════════════════════

SARVAM_URL = "https://api.sarvam.ai/v1/chat/completions"
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]
SARVAM_MODELS = [
    "sarvam-105b",
    "sarvam-105b-conversations",
]
DEFAULT_MODELS = {"sarvam": "sarvam-105b", "groq": "llama-3.3-70b-versatile"}

def _headers(provider: str, api_key: str) -> dict:
    if provider == "groq":
        return {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    return {"Content-Type": "application/json", "api-subscription-key": api_key}

def call_llm(text, year, era, provider, api_key, model=None, timeout=90) -> dict:
    if not api_key:
        raise ValueError("API key is required.")
    model   = model or DEFAULT_MODELS.get(provider, "sarvam-105b")
    prompt  = build_prompt_era2(text, year) if era == 2 else build_prompt_era1(text, year)
    url     = GROQ_URL if provider == "groq" else SARVAM_URL
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 1800,
    }
    try:
        resp = requests.post(url, headers=_headers(provider, api_key), json=payload, timeout=timeout)
    except requests.exceptions.Timeout:
        raise TimeoutError(f"Request timed out after {timeout}s.")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Network error: {e}")
    if not resp.ok:
        raise ValueError(f"API {resp.status_code}: {resp.text[:300]}")
    body    = resp.json()
    choices = body.get("choices") or []
    raw     = (choices[0].get("message", {}).get("content") or "") if choices else ""
    if not raw:
        raise ValueError(f"Empty response from API. Full body: {str(body)[:400]}")
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError(f"No JSON in response. Raw: {raw[:400]}")
    kpis = json.loads(m.group(0))
    return {k: (float(v) if v is not None and v != "null" and not isinstance(v, bool) else None)
            for k, v in kpis.items()}

def test_connection(provider, api_key, model=None):
    model = model or DEFAULT_MODELS.get(provider, "sarvam-105b")
    payload = {"model": model, "messages": [{"role": "user", "content": "Reply OK."}], "max_tokens": 5}
    try:
        r = requests.post(
            GROQ_URL if provider == "groq" else SARVAM_URL,
            headers=_headers(provider, api_key), json=payload, timeout=15,
        )
        return (True, f"Connected. Model: {model}") if r.ok else (False, f"Error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return False, f"Network error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# EDQI SCORING
# ══════════════════════════════════════════════════════════════════════════════

def _z_minmax(values, inv):
    valid = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    if len(valid) < 2:
        return [None] * len(values)
    mu  = sum(valid) / len(valid)
    sig = math.sqrt(sum((v - mu) ** 2 for v in valid) / len(valid)) or 1.0
    z   = [(float(v) - mu) / sig if v is not None else None for v in values]
    zv  = [x for x in z if x is not None]
    zmn, zmx = min(zv), max(zv)
    out = []
    for zi in z:
        if zi is None:
            out.append(None); continue
        sc = 50.0 if zmx == zmn else (zi - zmn) / (zmx - zmn) * 100.0
        out.append(round(max(0.0, min(100.0, 100.0 - sc if inv else sc)), 2))
    return out

def _score_group(group, ind_list):
    if not group:
        return group
    rows = [dict(r) for r in group]
    for ind in ind_list:
        iid = ind["id"]
        col = next((k for k in rows[0] if k == iid or k.startswith(iid + "_")), None)
        raw = [r.get(col) for r in rows] if col else [None] * len(rows)
        raw = [float(v) if v is not None else None for v in raw]
        for r, sc in zip(rows, _z_minmax(raw, ind["inv"])):
            r[f"_s_{iid}"] = sc
    for r in rows:
        for p in ("E", "S", "G"):
            pv = [r[f"_s_{i['id']}"] for i in ind_list if i["pillar"] == p and r.get(f"_s_{i['id']}") is not None]
            r[f"{p}_score"] = round(sum(pv) / len(pv), 2) if pv else None
        pv = [r.get(f"{p}_score") for p in ("E", "S", "G") if r.get(f"{p}_score") is not None]
        r["ESG_score"] = round(sum(pv) / len(pv), 2) if pv else None
        filled = sum(
            1 for i in ind_list
            if (c := next((k for k in r if k == i["id"] or k.startswith(i["id"] + "_")), None))
            and r.get(c) is not None
        )
        r["coverage_pct"] = round(filled / len(ind_list) * 100, 1)
    return rows

def compute_edqi(raw_records) -> pd.DataFrame:
    era1 = [r for r in raw_records if r.get("era") == 1]
    era2 = [r for r in raw_records if r.get("era") == 2]
    combined = sorted(_score_group(era1, ERA1_IND) + _score_group(era2, ERA2_IND),
                      key=lambda r: r.get("fiscal_year", 0))
    return pd.DataFrame(combined)

def build_panel_table(df, view="scores"):
    df = df.sort_values("fiscal_year").copy()
    df["fiscal_year"] = df["fiscal_year"].astype(int)
    if view == "scores":
        cols = [c for c in ["fiscal_year","era","E_score","S_score","G_score","ESG_score","coverage_pct"] if c in df.columns]
        return df[cols].set_index("fiscal_year")
    era_map = {"E_era1":(1,"E"),"S_era1":(1,"S"),"G_era1":(1,"G"),
               "E_era2":(2,"E"),"S_era2":(2,"S"),"G_era2":(2,"G")}
    if view not in era_map:
        return df.set_index("fiscal_year")
    era_id, pillar = era_map[view]
    ind_list = [i for i in (ERA1_IND if era_id == 1 else ERA2_IND) if i["pillar"] == pillar]
    sub = df[df["era"] == era_id].copy()
    if sub.empty:
        return sub
    raw_cols = [c for i in ind_list
                for c in sub.columns if c == i["id"] or c.startswith(i["id"] + "_")]
    return sub[["fiscal_year"] + raw_cols].set_index("fiscal_year")


# ══════════════════════════════════════════════════════════════════════════════
# STREAMLIT APP
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="EDQI Engine", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
[data-testid="stSidebar"] { background: #071629; }
[data-testid="stSidebar"] * { color: #cce5f8 !important; }
div[data-testid="metric-container"] {
    background: #0d1f38; border: 1px solid #14304f; border-radius: 10px; padding: 14px;
}
.era1 { background:#451a00; color:#fbbf24; padding:2px 10px; border-radius:4px; font-size:12px; font-weight:600; }
.era2 { background:#022c22; color:#34d399; padding:2px 10px; border-radius:4px; font-size:12px; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# Session state
for k, v in {"docs": [], "results": [], "scored_df": None,
             "manual_entries": [],
              "cfg": {"provider":"groq","api_key":"","model":DEFAULT_MODELS["groq"],
                      "company":"","bse":"","sector":""}}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 EDQI Engine")
    st.caption("ESG Disclosure Quality Index  \nBRR + BRSR · FY 2012–2025")
    st.divider()
    page = st.radio("Navigation",
        ["🔧 Configure", "📂 Upload", "⚡ Process", "✏️ Manual Entry", "📈 Results", "📤 Export"],
        label_visibility="collapsed")
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("ERA 1 BRR", "25", help="FY2012–2021 · E:9 S:10 G:6")
    c2.metric("ERA 2 BRSR", "32", help="FY2022–2025 · E:13 S:14 G:5")
    if st.session_state.scored_df is not None:
        st.divider()
        latest = st.session_state.scored_df.sort_values("fiscal_year").iloc[-1]
        if latest.get("ESG_score") is not None:
            st.metric(f"FY{int(latest['fiscal_year'])} ESG", f"{latest['ESG_score']:.1f}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Configure
# ══════════════════════════════════════════════════════════════════════════════
if page == "🔧 Configure":
    st.title("API Configuration")
    st.caption("Select your LLM provider and enter credentials. Groq is free — get a key at console.groq.com. Sarvam AI keys at api.sarvam.ai.")
    st.divider()

    col_prov, _ = st.columns([2, 3])
    with col_prov:
        provider_label = st.selectbox("AI Provider",
            ["Groq (free tier)", "Sarvam AI"],
            index=0 if st.session_state.cfg["provider"] == "groq" else 1)

    is_groq     = provider_label.startswith("Groq")
    provider_id = "groq" if is_groq else "sarvam"

    col_key, col_model = st.columns(2)
    with col_key:
        api_key = st.text_input(
            "Groq API Key" if is_groq else "Sarvam AI API Key",
            type="password",
            placeholder="gsk_…" if is_groq else "sk-sarvam-…",
            value=st.session_state.cfg.get("api_key", ""))
    with col_model:
        if is_groq:
            model = st.selectbox("Model", GROQ_MODELS)
        else:
            model = st.selectbox("Model", SARVAM_MODELS)

    st.divider()
    st.markdown("**Company Details**")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        company = st.text_input("Company Name", placeholder="e.g. Reliance Industries Ltd",
                                value=st.session_state.cfg.get("company", ""))
    with col_b:
        bse_code = st.text_input("BSE Code", placeholder="e.g. 500325",
                                 value=st.session_state.cfg.get("bse", ""))
    with col_c:
        sector = st.selectbox("Sector (GICS)", [
            "— Select —","Energy","Materials","Industrials","Consumer Discretionary",
            "Consumer Staples","Health Care","Financials","Information Technology",
            "Communication Services","Utilities","Real Estate"])

    st.divider()
    col_btn, col_res = st.columns([2, 5])
    with col_btn:
        if st.button("Test API Connection", type="secondary"):
            if not api_key:
                col_res.warning("Enter an API key first.")
            else:
                with st.spinner("Connecting…"):
                    ok, msg = test_connection(provider_id, api_key, model)
                (col_res.success if ok else col_res.error)(("✅ " if ok else "❌ ") + msg)

    st.session_state.cfg = {"provider": provider_id, "api_key": api_key, "model": model,
                             "company": company, "bse": bse_code, "sector": sector}
    st.info("After entering your key, go to **📂 Upload** to add PDFs, then **⚡ Process**.", icon="ℹ️")
    st.info("No API key? Use **✏️ Manual Entry** to enter indicator values directly — no API required.", icon="✏️")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Upload
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📂 Upload":
    st.title("Upload Annual Reports")
    st.caption("Up to 10 PDFs for the same company. Fiscal year is auto-detected — you can override below.")
    st.divider()

    uploaded_files = st.file_uploader("Drop PDF files here or click to browse",
                                      type=["pdf"], accept_multiple_files=True)

    if not uploaded_files:
        st.info("No files uploaded yet.", icon="📂")
    else:
        if len(uploaded_files) > 10:
            st.warning("Maximum 10 PDFs. Only the first 10 will be used.")
            uploaded_files = uploaded_files[:10]

        st.markdown("### File Queue")
        st.caption("FY ≥ 2022 → BRSR (ERA 2)  ·  FY < 2022 → BRR (ERA 1)")
        st.divider()

        queued = []
        for i, f in enumerate(uploaded_files):
            detected = detect_fiscal_year(f.name)
            col_n, col_sz, col_yr, col_era = st.columns([4, 1, 1, 2])
            col_n.markdown(f"**{f.name}**")
            col_sz.caption(f"{round(f.size/1024, 1)} KB")
            yr = col_yr.number_input("FY", min_value=2010, max_value=2030,
                                     value=int(detected) if detected else 2023,
                                     key=f"yr_{i}", label_visibility="collapsed")
            era = get_era(yr)
            col_era.markdown(
                f'<span class="era{"2" if era==2 else "1"}">{"ERA 2 — BRSR" if era==2 else "ERA 1 — BRR"}</span>',
                unsafe_allow_html=True)
            queued.append({"file": f, "name": f.name, "year": yr, "era": era,
                           "size_kb": round(f.size/1024, 1)})

        st.divider()
        st.session_state.docs = queued
        st.success(f"{len(queued)} file(s) queued. Go to **⚡ Process** to run extraction.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Process
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Process":
    st.title("Extract & Score")
    cfg  = st.session_state.cfg
    docs = st.session_state.docs

    if not cfg.get("api_key"):
        st.warning("Go to **🔧 Configure** and enter your API key first."); st.stop()
    if not docs:
        st.warning("Go to **📂 Upload** and add PDF files first."); st.stop()

    col_l, col_r = st.columns([3, 2])
    col_l.markdown(f"**{len(docs)} document(s) queued**  \n"
                   f"Company: `{cfg.get('company') or '—'}`  \n"
                   f"Provider: `{cfg['provider'].upper()}`  ·  Model: `{cfg['model']}`")
    col_r.metric("BRR docs (ERA 1)", sum(1 for d in docs if d["era"] == 1))
    col_r.metric("BRSR docs (ERA 2)", sum(1 for d in docs if d["era"] == 2))
    st.divider()

    if st.button("▶ Start Extraction", type="primary", use_container_width=True):
        results  = []
        progress = st.progress(0, text="Starting…")
        log_box  = st.empty()
        log_lines: list[str] = []

        def log(msg):
            log_lines.append(msg)
            log_box.code("\n".join(log_lines[-16:]), language=None)

        for i, doc in enumerate(docs):
            label = f"[{i+1}/{len(docs)}]  {doc['name']}  (FY{doc['year']})"
            progress.progress(i / len(docs), text=label)
            log(f"\n{'─'*60}\n▶  {label}")
            try:
                log("   Extracting PDF text…")
                file_bytes = doc["file"].read(); doc["file"].seek(0)
                full_text  = extract_pdf_text(file_bytes)
                log(f"   ✓ {len(full_text):,} characters extracted")

                esg_text = find_esg_section(full_text)
                log(f"   ✓ ESG section: {len(esg_text):,} characters")

                log(f"   Calling {cfg['provider'].upper()} API…")
                kpis = call_llm(esg_text, doc["year"], doc["era"],
                                cfg["provider"], cfg["api_key"], cfg["model"])

                record = {"company": cfg.get("company",""), "bse_code": cfg.get("bse",""),
                          "sector": cfg.get("sector",""), "fiscal_year": doc["year"],
                          "era": doc["era"], "source_file": doc["name"]}
                record.update(kpis)
                results.append(record)

                n_filled = sum(1 for v in kpis.values() if v is not None)
                n_total  = len(era_indicators(doc["era"]))
                log(f"   ✅ {n_filled}/{n_total} indicators extracted")

            except Exception as exc:
                log(f"   ❌ Error: {str(exc)[:120]}")

            progress.progress((i+1) / len(docs), text=label)

        log(f"\n{'─'*60}")
        if results:
            log(f"Computing EDQI scores for {len(results)} record(s)…")
            st.session_state.results   = results
            st.session_state.scored_df = compute_edqi(results)
            log("✅ Scoring complete.")
            st.success(f"Processed {len(results)}/{len(docs)} document(s). Go to **📈 Results**.")
        else:
            st.error("No documents were processed successfully.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Manual Entry (No API)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "✏️ Manual Entry":
    st.title("Manual Data Entry")
    st.caption(
        "Enter indicator values directly from the annual report — no API key required. "
        "Add one fiscal year at a time. Results feed into the same EDQI scoring pipeline."
    )
    st.divider()

    cfg = st.session_state.cfg

    # ── Company details (shared with Configure) ──────────────────────────────
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        me_company = st.text_input("Company Name", value=cfg.get("company", ""),
                                   key="me_company", placeholder="e.g. Reliance Industries Ltd")
    with col_b:
        me_bse = st.text_input("BSE Code", value=cfg.get("bse", ""),
                               key="me_bse", placeholder="e.g. 500325")
    with col_c:
        me_sector = st.selectbox("Sector (GICS)", [
            "— Select —", "Energy", "Materials", "Industrials",
            "Consumer Discretionary", "Consumer Staples", "Health Care",
            "Financials", "Information Technology",
            "Communication Services", "Utilities", "Real Estate"],
            key="me_sector")

    st.divider()

    # ── Fiscal year + ERA ─────────────────────────────────────────────────────
    col_yr, col_era, _ = st.columns([2, 2, 3])
    with col_yr:
        me_year = st.number_input("Fiscal Year", min_value=2010, max_value=2030,
                                  value=2023, step=1, key="me_year")
    me_era = get_era(int(me_year))
    with col_era:
        st.metric("ERA", f"ERA {me_era} — {'BRSR' if me_era == 2 else 'BRR'}",
                  help="Auto-detected: FY ≥ 2022 → ERA 2 (BRSR), FY < 2022 → ERA 1 (BRR)")

    ind_list = era_indicators(me_era)
    pillars  = sorted({i["pillar"] for i in ind_list})
    p_labels = {"E": "🌿 Environmental", "S": "👥 Social", "G": "🏛 Governance"}

    st.markdown(f"**Enter values for FY{int(me_year)} — {'BRSR (32 KPIs)' if me_era == 2 else 'BRR (25 KPIs)'}**")
    st.caption("Leave a field blank or 0 if the value is not disclosed. Percentages should be on a 0–100 scale.")

    form_vals: dict[str, float | None] = {}

    for p in pillars:
        st.markdown(f"##### {p_labels.get(p, p)}")
        p_inds = [i for i in ind_list if i["pillar"] == p]
        cols   = st.columns(3)
        for idx, ind in enumerate(p_inds):
            with cols[idx % 3]:
                inv_note = " ↓" if ind["inv"] else ""
                raw = st.text_input(
                    f"{ind['id']} · {ind['name']}{inv_note}",
                    placeholder=f"({ind['unit']})",
                    key=f"me_{me_year}_{ind['id']}",
                    help=f"Unit: {ind['unit']}{'  |  Lower is better' if ind['inv'] else ''}"
                )
                try:
                    form_vals[ind["id"]] = float(raw) if raw.strip() else None
                except ValueError:
                    form_vals[ind["id"]] = None
        st.divider()

    col_btn, col_msg = st.columns([2, 5])
    with col_btn:
        add_clicked = st.button("➕ Add This Year", type="primary", use_container_width=True)

    if add_clicked:
        record = {
            "company":     me_company,
            "bse_code":    me_bse,
            "sector":      me_sector if me_sector != "— Select —" else "",
            "fiscal_year": int(me_year),
            "era":         me_era,
            "source_file": f"manual_fy{int(me_year)}",
        }
        record.update(form_vals)
        # Replace if same year already exists
        st.session_state.manual_entries = [
            e for e in st.session_state.manual_entries
            if e.get("fiscal_year") != int(me_year)
        ]
        st.session_state.manual_entries.append(record)
        n_filled = sum(1 for v in form_vals.values() if v is not None)
        col_msg.success(
            f"FY{int(me_year)} added — {n_filled}/{len(ind_list)} indicators filled. "
            f"Total years in queue: {len(st.session_state.manual_entries)}."
        )

    # ── Queued entries ────────────────────────────────────────────────────────
    if st.session_state.manual_entries:
        st.markdown("---")
        st.markdown("**Years in Queue**")
        queue_df = pd.DataFrame([{
            "Fiscal Year": e["fiscal_year"],
            "ERA":         f"ERA {e['era']} — {'BRSR' if e['era']==2 else 'BRR'}",
            "Indicators Filled": sum(
                1 for i in era_indicators(e["era"])
                if e.get(i["id"]) is not None
            ),
            "Total KPIs": len(era_indicators(e["era"])),
        } for e in sorted(st.session_state.manual_entries, key=lambda x: x["fiscal_year"])])
        st.dataframe(queue_df.set_index("Fiscal Year"), use_container_width=True)

        col_run, col_clr, col_info = st.columns([2, 2, 4])
        with col_run:
            if st.button("⚡ Compute EDQI Scores", type="primary", use_container_width=True):
                if len(st.session_state.manual_entries) < 2:
                    col_info.warning(
                        "EDQI scoring requires at least 2 years within an era for z-normalisation. "
                        "Add more years."
                    )
                else:
                    st.session_state.results   = st.session_state.manual_entries
                    st.session_state.scored_df = compute_edqi(st.session_state.manual_entries)
                    # Sync company info to cfg
                    st.session_state.cfg["company"] = me_company
                    st.session_state.cfg["bse"]     = me_bse
                    st.session_state.cfg["sector"]  = me_sector
                    col_info.success(
                        f"EDQI scores computed for {len(st.session_state.manual_entries)} year(s). "
                        f"Go to **📈 Results** to view."
                    )
        with col_clr:
            if st.button("🗑 Clear Queue", use_container_width=True):
                st.session_state.manual_entries = []
                st.rerun()
    else:
        st.info(
            "No years queued yet. Fill in the values above and click **➕ Add This Year**.",
            icon="✏️"
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Results
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Results":
    st.title("EDQI Results")
    scored_df = st.session_state.get("scored_df")
    cfg       = st.session_state.cfg

    if scored_df is None or scored_df.empty:
        st.info("No results yet. Run **⚡ Process** first.", icon="📊"); st.stop()

    df = scored_df.sort_values("fiscal_year").copy()
    df["fiscal_year"] = df["fiscal_year"].astype(int)
    latest = df.iloc[-1]

    st.markdown(f"### {cfg.get('company') or 'Company'}")
    st.caption(f"FY{df['fiscal_year'].min()} – FY{df['fiscal_year'].max()}  ·  {len(df)} year(s) scored")
    st.divider()

    def _fmt(v): return f"{v:.1f}" if v is not None else "—"
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("ESG Score",  _fmt(latest.get("ESG_score")),  help="EDQI composite (0–100)")
    c2.metric("E Score",    _fmt(latest.get("E_score")),    help="Environmental pillar")
    c3.metric("S Score",    _fmt(latest.get("S_score")),    help="Social pillar")
    c4.metric("G Score",    _fmt(latest.get("G_score")),    help="Governance pillar")
    c5.metric("Coverage",   f"{latest.get('coverage_pct', 0):.0f}%")
    st.caption(f"Latest year: FY{int(latest['fiscal_year'])}")
    st.divider()

    tab_charts, tab_data = st.tabs(["📊 Charts", "🗂 Panel Data"])

    with tab_charts:
        years = df["fiscal_year"].tolist()
        fig   = go.Figure()
        for col, clr, lbl, w in [("ESG_score","#00d4a1","ESG Composite",2.5),
                                   ("E_score","#22c55e","Environmental",1.5),
                                   ("S_score","#3b82f6","Social",1.5),
                                   ("G_score","#a855f7","Governance",1.5)]:
            if col in df.columns:
                fig.add_trace(go.Scatter(x=years, y=df[col].tolist(), mode="lines+markers",
                                         name=lbl, line=dict(color=clr, width=w),
                                         marker=dict(size=7)))
        fig.update_layout(title="EDQI Score Trend", xaxis_title="Fiscal Year",
                          yaxis_title="Score (0–100)", yaxis=dict(range=[0,100]),
                          template="plotly_dark", height=420,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig, use_container_width=True)

        if "coverage_pct" in df.columns:
            fig2 = go.Figure(go.Bar(x=years, y=df["coverage_pct"].tolist(),
                                    marker_color="#3b82f6",
                                    text=[f"{v:.0f}%" for v in df["coverage_pct"]],
                                    textposition="outside"))
            fig2.update_layout(title="Indicator Coverage per Year", xaxis_title="Fiscal Year",
                                yaxis_title="Coverage (%)", yaxis=dict(range=[0,110]),
                                template="plotly_dark", height=300)
            st.plotly_chart(fig2, use_container_width=True)

    with tab_data:
        view = st.selectbox("View", ["EDQI Scores","BRR — Environmental","BRR — Social",
                                      "BRR — Governance","BRSR — Environmental",
                                      "BRSR — Social","BRSR — Governance"])
        key  = {"EDQI Scores":"scores","BRR — Environmental":"E_era1","BRR — Social":"S_era1",
                "BRR — Governance":"G_era1","BRSR — Environmental":"E_era2",
                "BRSR — Social":"S_era2","BRSR — Governance":"G_era2"}[view]
        panel = build_panel_table(scored_df, view=key)
        if panel.empty:
            st.info("No data for this view — no documents from the corresponding era were processed.")
        else:
            st.dataframe(panel.round(2), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Export
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📤 Export":
    st.title("Export Data")
    scored_df = st.session_state.get("scored_df")
    results   = st.session_state.get("results", [])
    cfg       = st.session_state.cfg

    if scored_df is None or scored_df.empty:
        st.info("No results to export. Run **⚡ Process** first.", icon="📤"); st.stop()

    slug = (cfg.get("company") or "Company").replace(" ", "_")
    st.markdown("### Download")
    st.divider()

    col_csv, col_xlsx, col_json = st.columns(3)

    with col_csv:
        buf = io.StringIO(); scored_df.to_csv(buf, index=False)
        st.download_button("⬇ CSV — All columns", buf.getvalue().encode(),
                           file_name=f"EDQI_{slug}.csv", mime="text/csv",
                           use_container_width=True)
        st.caption("Full scored DataFrame.")

    with col_xlsx:
        xbuf = io.BytesIO()
        with pd.ExcelWriter(xbuf, engine="openpyxl") as w:
            score_cols = [c for c in ["fiscal_year","era","E_score","S_score","G_score","ESG_score","coverage_pct"] if c in scored_df.columns]
            scored_df[score_cols].to_excel(w, sheet_name="EDQI_Scores", index=False)

            brr = scored_df[scored_df["era"]==1]
            if not brr.empty:
                era1_cols = ["fiscal_year"] + [i["id"] for i in ERA1_IND if i["id"] in brr.columns]
                brr[[c for c in era1_cols if c in brr.columns]].to_excel(w, sheet_name="BRR_Indicators", index=False)

            brsr = scored_df[scored_df["era"]==2]
            if not brsr.empty:
                era2_cols = ["fiscal_year"] + [i["id"] for i in ERA2_IND if i["id"] in brsr.columns]
                brsr[[c for c in era2_cols if c in brsr.columns]].to_excel(w, sheet_name="BRSR_Indicators", index=False)

            meta = [{"ID":i["id"],"Era":f"ERA {i['era']}","Pillar":i["pillar"],
                     "Name":i["name"],"Unit":i["unit"],"Lower is Better":i["inv"]}
                    for i in ERA1_IND + ERA2_IND]
            pd.DataFrame(meta).to_excel(w, sheet_name="Indicator_Metadata", index=False)

        st.download_button("⬇ Excel — 4 sheets", xbuf.getvalue(),
                           file_name=f"EDQI_{slug}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
        st.caption("EDQI Scores · BRR · BRSR · Metadata.")

    with col_json:
        st.download_button("⬇ JSON — Raw extractions",
                           json.dumps(results, indent=2, ensure_ascii=False).encode(),
                           file_name=f"EDQI_{slug}_raw.json", mime="application/json",
                           use_container_width=True)
        st.caption("Raw KPI values before scoring.")

    st.divider()
    st.markdown("**Preview — EDQI Scores**")
    score_cols = [c for c in ["fiscal_year","era","E_score","S_score","G_score","ESG_score","coverage_pct"] if c in scored_df.columns]
    st.dataframe(scored_df[score_cols].sort_values("fiscal_year").set_index("fiscal_year").round(2),
                 use_container_width=True)
