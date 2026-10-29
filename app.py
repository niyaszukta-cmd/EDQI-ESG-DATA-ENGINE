"""
app.py  —  EDQI Engine  (Streamlit)
ESG Disclosure Quality Index · BRR (ERA 1) + BRSR (ERA 2) · FY2012-2025

Run:
    streamlit run app.py

Requirements:
    pip install -r requirements.txt
"""

from __future__ import annotations

import io
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from edqi import build_panel_table, compute_edqi
from indicators import ERA1_IND, ERA2_IND, get_era, era_indicators
from llm import DEFAULT_MODELS, GROQ_MODELS, call_llm, test_connection
from pdf_utils import detect_fiscal_year, extract_pdf_text, find_esg_section

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EDQI Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Sidebar background */
    [data-testid="stSidebar"] { background: #071629; }
    [data-testid="stSidebar"] * { color: #cce5f8 !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label { color: #5588a8 !important; }

    /* Score cards */
    div[data-testid="metric-container"] {
        background: #0d1f38;
        border: 1px solid #14304f;
        border-radius: 10px;
        padding: 14px;
    }

    /* ERA badges */
    .era1-badge {
        background: #451a00; color: #fbbf24;
        padding: 2px 10px; border-radius: 4px;
        font-size: 12px; font-weight: 600;
    }
    .era2-badge {
        background: #022c22; color: #34d399;
        padding: 2px 10px; border-radius: 4px;
        font-size: 12px; font-weight: 600;
    }

    /* Section headers */
    .section-title {
        font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
        text-transform: uppercase; color: #5588a8; margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ──────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "docs":      [],       # list of dicts: file, name, year, era, size_kb
        "results":   [],       # list of raw extraction records
        "scored_df": None,     # DataFrame from compute_edqi()
        "cfg": {
            "provider": "groq",
            "api_key":  "",
            "model":    DEFAULT_MODELS["groq"],
            "company":  "",
            "bse":      "",
            "sector":   "",
        },
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 EDQI Engine")
    st.caption("ESG Disclosure Quality Index")
    st.caption("BRR + BRSR · FY 2012 – 2025")
    st.divider()

    page = st.radio(
        "Navigation",
        ["🔧 Configure", "📂 Upload", "⚡ Process", "📈 Results", "📤 Export"],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown('<div class="section-title">Indicator Coverage</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("ERA 1 BRR", "25", help="FY2012–2021 · E:9 S:10 G:6")
    c2.metric("ERA 2 BRSR", "32", help="FY2022–2025 · E:13 S:14 G:5")

    if st.session_state.scored_df is not None:
        st.divider()
        df = st.session_state.scored_df
        n_years = len(df)
        latest  = df.sort_values("fiscal_year").iloc[-1]
        st.markdown('<div class="section-title">Last Run</div>', unsafe_allow_html=True)
        st.caption(f"{n_years} year(s) scored")
        if latest.get("ESG_score") is not None:
            st.metric(
                f"FY{int(latest['fiscal_year'])} ESG",
                f"{latest['ESG_score']:.1f}",
                help="EDQI composite (0–100)",
            )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Configure
# ══════════════════════════════════════════════════════════════════════════════
if page == "🔧 Configure":
    st.title("API Configuration")
    st.caption(
        "Select your LLM provider, enter credentials, and fill in company details. "
        "Groq is free to use; get a key at console.groq.com. "
        "Sarvam AI keys are available at api.sarvam.ai."
    )
    st.divider()

    # Provider selection
    col_prov, col_spacer = st.columns([2, 3])
    with col_prov:
        provider_label = st.selectbox(
            "AI Provider",
            ["Groq (free tier)", "Sarvam AI"],
            index=0 if st.session_state.cfg["provider"] == "groq" else 1,
            help="Both providers support the OpenAI-compatible chat completions format.",
        )

    is_groq = provider_label.startswith("Groq")
    provider_id = "groq" if is_groq else "sarvam"

    st.markdown("")  # spacing

    col_key, col_model = st.columns(2)
    with col_key:
        api_key = st.text_input(
            "Groq API Key" if is_groq else "Sarvam AI API Key",
            type="password",
            placeholder="gsk_…" if is_groq else "sk-sarvam-…",
            value=st.session_state.cfg.get("api_key", ""),
            help="Stored in session memory only — never sent anywhere except the chosen provider.",
        )

    with col_model:
        if is_groq:
            model = st.selectbox(
                "Model",
                GROQ_MODELS,
                index=0,
                help="llama-3.3-70b-versatile is the default recommendation.",
            )
        else:
            model = st.text_input(
                "Model",
                value="sarvam-m",
                help="sarvam-m is recommended for document intelligence tasks.",
            )

    st.divider()
    st.markdown("**Company Details**")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        company = st.text_input(
            "Company Name",
            placeholder="e.g. Reliance Industries Ltd",
            value=st.session_state.cfg.get("company", ""),
        )
    with col_b:
        bse_code = st.text_input(
            "BSE Code",
            placeholder="e.g. 500325",
            value=st.session_state.cfg.get("bse", ""),
        )
    with col_c:
        sector = st.selectbox(
            "Sector (GICS)",
            [
                "— Select —", "Energy", "Materials", "Industrials",
                "Consumer Discretionary", "Consumer Staples", "Health Care",
                "Financials", "Information Technology",
                "Communication Services", "Utilities", "Real Estate",
            ],
            index=0,
        )

    st.divider()
    col_btn, col_result = st.columns([2, 5])
    with col_btn:
        if st.button("Test API Connection", type="secondary"):
            if not api_key:
                st.warning("Enter an API key first.")
            else:
                with st.spinner("Connecting…"):
                    ok, msg = test_connection(provider_id, api_key, model)
                col_result.success(f"✅ {msg}") if ok else col_result.error(f"❌ {msg}")

    # Persist config to session state
    st.session_state.cfg = {
        "provider": provider_id,
        "api_key":  api_key,
        "model":    model,
        "company":  company,
        "bse":      bse_code,
        "sector":   sector,
    }

    st.info(
        "After saving your key, go to **📂 Upload** to add annual report PDFs, "
        "then **⚡ Process** to run extraction.",
        icon="ℹ️",
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Upload
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📂 Upload":
    st.title("Upload Annual Reports")
    st.caption(
        "Upload up to 10 PDF annual reports for the same company. "
        "The fiscal year is detected automatically from the filename or document text — "
        "you can override it below."
    )
    st.divider()

    uploaded_files = st.file_uploader(
        "Drop PDF files here, or click to browse",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info("No files uploaded yet.", icon="📂")
    else:
        if len(uploaded_files) > 10:
            st.warning("Maximum 10 PDFs. Only the first 10 will be queued.")
            uploaded_files = uploaded_files[:10]

        st.markdown("### File Queue")
        st.caption(
            "Verify the detected fiscal year for each file. "
            "ERA is set automatically: FY ≥ 2022 → BRSR (ERA 2), FY < 2022 → BRR (ERA 1)."
        )
        st.divider()

        queued = []
        for i, f in enumerate(uploaded_files):
            detected = detect_fiscal_year(f.name, "")

            col_name, col_size, col_yr, col_era = st.columns([4, 1, 1, 2])
            with col_name:
                st.markdown(f"**{f.name}**")
            with col_size:
                st.caption(f"{round(f.size / 1024, 1)} KB")
            with col_yr:
                yr = st.number_input(
                    "FY",
                    min_value=2010,
                    max_value=2030,
                    value=int(detected) if detected else 2023,
                    key=f"yr_{i}",
                    label_visibility="collapsed",
                )
            with col_era:
                era = get_era(yr)
                badge_class = "era2-badge" if era == 2 else "era1-badge"
                badge_text  = "ERA 2 — BRSR" if era == 2 else "ERA 1 — BRR"
                st.markdown(
                    f'<span class="{badge_class}">{badge_text}</span>',
                    unsafe_allow_html=True,
                )

            queued.append({
                "file":    f,
                "name":    f.name,
                "year":    yr,
                "era":     era,
                "size_kb": round(f.size / 1024, 1),
            })

        st.divider()
        st.session_state.docs = queued
        st.success(
            f"{len(queued)} file(s) queued. "
            "Go to **⚡ Process** to run extraction."
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Process
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Process":
    st.title("Extract & Score")

    cfg  = st.session_state.cfg
    docs = st.session_state.docs

    # Guard conditions
    if not cfg.get("api_key"):
        st.warning("Go to **🔧 Configure** and enter your API key first.")
        st.stop()

    if not docs:
        st.warning("Go to **📂 Upload** and add PDF files first.")
        st.stop()

    # Summary before run
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown(
            f"**{len(docs)} document(s) queued**  \n"
            f"Company: `{cfg.get('company') or '—'}`  \n"
            f"Provider: `{cfg['provider'].upper()}`  ·  Model: `{cfg['model']}`"
        )
    with col_r:
        era1_count = sum(1 for d in docs if d["era"] == 1)
        era2_count = sum(1 for d in docs if d["era"] == 2)
        st.metric("BRR docs (ERA 1)", era1_count)
        st.metric("BRSR docs (ERA 2)", era2_count)

    st.divider()

    if st.button("▶ Start Extraction", type="primary", use_container_width=True):
        results      = []
        progress_bar = st.progress(0, text="Starting…")
        log_display  = st.empty()
        log_lines: list[str] = []

        def log(msg: str):
            log_lines.append(msg)
            log_display.code("\n".join(log_lines[-16:]), language=None)

        for i, doc in enumerate(docs):
            label = f"[{i+1}/{len(docs)}]  {doc['name']}  (FY{doc['year']})"
            progress_bar.progress(i / len(docs), text=label)
            log(f"\n{'─'*60}")
            log(f"▶  {label}")

            try:
                # Step 1: extract PDF text
                log("   Extracting PDF text…")
                file_bytes = doc["file"].read()
                doc["file"].seek(0)
                full_text = extract_pdf_text(file_bytes)
                log(f"   ✓  {len(full_text):,} characters extracted")

                # Step 2: locate ESG-dense section
                esg_text = find_esg_section(full_text)
                log(f"   ✓  ESG section: {len(esg_text):,} characters")

                # Step 3: LLM call
                log(f"   Calling {cfg['provider'].upper()} API…")
                kpis = call_llm(
                    text=esg_text,
                    year=doc["year"],
                    era=doc["era"],
                    provider=cfg["provider"],
                    api_key=cfg["api_key"],
                    model=cfg["model"],
                )

                # Step 4: build record
                record: dict = {
                    "company":     cfg.get("company", ""),
                    "bse_code":    cfg.get("bse", ""),
                    "sector":      cfg.get("sector", ""),
                    "fiscal_year": doc["year"],
                    "era":         doc["era"],
                    "source_file": doc["name"],
                }
                record.update(kpis)
                results.append(record)

                n_filled = sum(1 for v in kpis.values() if v is not None)
                n_total  = len(era_indicators(doc["era"]))
                log(f"   ✅  {n_filled}/{n_total} indicators extracted")

            except Exception as exc:
                log(f"   ❌  Error: {str(exc)[:120]}")

            progress_bar.progress((i + 1) / len(docs), text=label)

        log("\n" + "─" * 60)

        if results:
            log(f"Computing EDQI scores for {len(results)} record(s)…")
            scored_df = compute_edqi(results)
            st.session_state.results   = results
            st.session_state.scored_df = scored_df
            log("✅  Scoring complete.")
            st.success(
                f"Processed {len(results)} of {len(docs)} document(s). "
                "Go to **📈 Results** to view scores."
            )
        else:
            st.error("No documents were processed successfully. Check logs above.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Results
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Results":
    st.title("EDQI Results")

    scored_df = st.session_state.get("scored_df")
    cfg       = st.session_state.cfg

    if scored_df is None or scored_df.empty:
        st.info("No results yet. Run **⚡ Process** first.", icon="📊")
        st.stop()

    df_sorted = scored_df.sort_values("fiscal_year").copy()
    df_sorted["fiscal_year"] = df_sorted["fiscal_year"].astype(int)
    latest = df_sorted.iloc[-1]

    # Summary row
    company_label = cfg.get("company") or "Company"
    st.markdown(f"### {company_label}")
    st.caption(
        f"FY{df_sorted['fiscal_year'].min()} – FY{df_sorted['fiscal_year'].max()}  ·  "
        f"{len(df_sorted)} year(s) scored"
    )
    st.divider()

    # Latest year KPI cards
    c1, c2, c3, c4, c5 = st.columns(5)
    def _fmt(val) -> str:
        return f"{val:.1f}" if val is not None else "—"

    c1.metric("ESG Score",     _fmt(latest.get("ESG_score")),   help="EDQI composite (0–100)")
    c2.metric("E Score",       _fmt(latest.get("E_score")),     help="Environmental pillar")
    c3.metric("S Score",       _fmt(latest.get("S_score")),     help="Social pillar")
    c4.metric("G Score",       _fmt(latest.get("G_score")),     help="Governance pillar")
    c5.metric("Coverage",      f"{latest.get('coverage_pct', 0):.0f}%", help="Indicators filled")
    st.caption(f"Latest year: FY{int(latest['fiscal_year'])}")

    st.divider()

    # Tabs: Charts | Panel Data
    tab_charts, tab_data = st.tabs(["📊 Charts", "🗂 Panel Data"])

    with tab_charts:
        years = df_sorted["fiscal_year"].tolist()

        # ESG trend line chart
        fig = go.Figure()
        series_cfg = [
            ("ESG_score", "#00d4a1", "ESG Composite", 2.5),
            ("E_score",   "#22c55e", "Environmental",  1.5),
            ("S_score",   "#3b82f6", "Social",         1.5),
            ("G_score",   "#a855f7", "Governance",     1.5),
        ]
        for col, clr, label, width in series_cfg:
            if col in df_sorted.columns:
                fig.add_trace(go.Scatter(
                    x=years,
                    y=df_sorted[col].tolist(),
                    mode="lines+markers",
                    name=label,
                    line=dict(color=clr, width=width),
                    marker=dict(size=7),
                ))

        fig.update_layout(
            title="EDQI Score Trend",
            xaxis_title="Fiscal Year",
            yaxis_title="Score (0 – 100)",
            yaxis=dict(range=[0, 100]),
            template="plotly_dark",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=20, t=60, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Indicator coverage bar chart
        if "coverage_pct" in df_sorted.columns:
            fig2 = go.Figure(go.Bar(
                x=years,
                y=df_sorted["coverage_pct"].tolist(),
                marker_color="#3b82f6",
                text=[f"{v:.0f}%" for v in df_sorted["coverage_pct"]],
                textposition="outside",
            ))
            fig2.update_layout(
                title="Indicator Coverage per Year",
                xaxis_title="Fiscal Year",
                yaxis_title="Coverage (%)",
                yaxis=dict(range=[0, 110]),
                template="plotly_dark",
                height=300,
                margin=dict(l=40, r=20, t=50, b=40),
            )
            st.plotly_chart(fig2, use_container_width=True)

    with tab_data:
        view = st.selectbox(
            "View",
            [
                "EDQI Scores",
                "BRR — Environmental",
                "BRR — Social",
                "BRR — Governance",
                "BRSR — Environmental",
                "BRSR — Social",
                "BRSR — Governance",
            ],
        )

        view_key_map = {
            "EDQI Scores":           "scores",
            "BRR — Environmental":   "E_era1",
            "BRR — Social":          "S_era1",
            "BRR — Governance":      "G_era1",
            "BRSR — Environmental":  "E_era2",
            "BRSR — Social":         "S_era2",
            "BRSR — Governance":     "G_era2",
        }
        panel = build_panel_table(scored_df, view=view_key_map[view])

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
        st.info("No results to export. Run **⚡ Process** first.", icon="📤")
        st.stop()

    company_slug = (cfg.get("company") or "Company").replace(" ", "_")

    st.markdown("### Download")
    st.caption("Three formats available: CSV (flat), Excel (4 sheets), and JSON (raw extractions).")
    st.divider()

    col_csv, col_xlsx, col_json = st.columns(3)

    # CSV
    with col_csv:
        csv_buf = io.StringIO()
        scored_df.to_csv(csv_buf, index=False)
        st.download_button(
            label="⬇ CSV — All columns",
            data=csv_buf.getvalue().encode("utf-8"),
            file_name=f"EDQI_{company_slug}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.caption("Full scored DataFrame including all raw and scored columns.")

    # Excel
    with col_xlsx:
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:

            # Sheet 1: EDQI Scores
            score_cols = [
                c for c in
                ["fiscal_year", "era", "E_score", "S_score", "G_score", "ESG_score", "coverage_pct"]
                if c in scored_df.columns
            ]
            scored_df[score_cols].to_excel(writer, sheet_name="EDQI_Scores", index=False)

            # Sheet 2: BRR Indicators
            brr_df = scored_df[scored_df["era"] == 1].copy()
            if not brr_df.empty:
                era1_raw_cols = ["fiscal_year"] + [
                    i["id"] for i in ERA1_IND if i["id"] in brr_df.columns
                ]
                brr_df[[c for c in era1_raw_cols if c in brr_df.columns]].to_excel(
                    writer, sheet_name="BRR_Indicators", index=False
                )

            # Sheet 3: BRSR Indicators
            brsr_df = scored_df[scored_df["era"] == 2].copy()
            if not brsr_df.empty:
                era2_raw_cols = ["fiscal_year"] + [
                    i["id"] for i in ERA2_IND if i["id"] in brsr_df.columns
                ]
                brsr_df[[c for c in era2_raw_cols if c in brsr_df.columns]].to_excel(
                    writer, sheet_name="BRSR_Indicators", index=False
                )

            # Sheet 4: Indicator Metadata
            meta_rows = [
                {
                    "ID": i["id"],
                    "Era": f"ERA {i['era']}",
                    "Pillar": i["pillar"],
                    "Name": i["name"],
                    "Unit": i["unit"],
                    "Lower is Better": i["inv"],
                }
                for i in ERA1_IND + ERA2_IND
            ]
            pd.DataFrame(meta_rows).to_excel(
                writer, sheet_name="Indicator_Metadata", index=False
            )

        st.download_button(
            label="⬇ Excel — 4 sheets",
            data=excel_buf.getvalue(),
            file_name=f"EDQI_{company_slug}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption("Sheets: EDQI Scores, BRR Indicators, BRSR Indicators, Metadata.")

    # JSON
    with col_json:
        st.download_button(
            label="⬇ JSON — Raw extractions",
            data=json.dumps(results, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name=f"EDQI_{company_slug}_raw.json",
            mime="application/json",
            use_container_width=True,
        )
        st.caption("Raw LLM-extracted KPI values before scoring.")

    st.divider()
    st.markdown("**Preview — EDQI Scores**")
    score_cols = [
        c for c in
        ["fiscal_year", "era", "E_score", "S_score", "G_score", "ESG_score", "coverage_pct"]
        if c in scored_df.columns
    ]
    st.dataframe(
        scored_df[score_cols]
        .sort_values("fiscal_year")
        .set_index("fiscal_year")
        .round(2),
        use_container_width=True,
    )
