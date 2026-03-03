"""
SyDRe — Systematic Document Retrieval
Streamlit Browser UI — v2.0
"""

import streamlit as st
import sys
import tempfile
import shutil
import zipfile
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from rules_reader import load_rules
from pipeline import run_pipeline
from excel_writer import write_excel

BASE_DIR = Path(__file__).parent
RULES_PATH = BASE_DIR / "rules.txt"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SyDRe",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state initialisation ───────────────────────────────────────────────
# All pipeline results are stored here. This means widget interactions
# (changing dropdowns, expanding snippets, filtering by rule) never
# re-trigger the pipeline — only clicking Run does.
if "results" not in st.session_state:
    st.session_state.results = []
if "excel_path" not in st.session_state:
    st.session_state.excel_path = None
if "run_logs" not in st.session_state:
    st.session_state.run_logs = []
if "last_run_summary" not in st.session_state:
    st.session_state.last_run_summary = None

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 SyDRe")
    st.caption("Systematic Document Retrieval")
    st.divider()

    # --- Rules editor ---
    st.subheader("📋 Eligibility Rules")

    if RULES_PATH.exists():
        current_rules_text = RULES_PATH.read_text(encoding="utf-8")
    else:
        current_rules_text = (
            "1. Minimum average annual turnover of 5 crore in last 3 financial years\n"
            "2. OEM authorization certificate from original manufacturer required\n"
            "3. Valid GST registration certificate must be submitted\n"
        )

    edited_rules = st.text_area(
        label="Edit rules below (numbered list format):",
        value=current_rules_text,
        height=280,
        help="Each rule must start with a number and full stop: 1. Rule text",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns(2)
    with col1:
        save_clicked = st.button("💾 Save Rules", use_container_width=True, type="primary")
    with col2:
        top_n = st.number_input("Top N", min_value=1, max_value=20, value=5)

    if save_clicked:
        try:
            RULES_PATH.write_text(edited_rules, encoding="utf-8")
            rules = load_rules(RULES_PATH)
            st.success(f"✅ {len(rules)} rule(s) saved")
            for r in rules:
                st.caption(f"{r['rule_id']}: {r['rule_text'][:50]}{'...' if len(r['rule_text']) > 50 else ''}")
        except ValueError as e:
            st.error(f"Format error: {e}")

    st.divider()
    st.caption("Format: `1. Rule text`")
    st.caption("One rule per line · Min 1 rule")
    st.caption(f"Saved to: `{RULES_PATH}`")


# ── Main area ───────────────────────────────────────────────────────────────────
st.title("SyDRe — Systematic Document Retrieval")
st.caption("Upload vendor ZIPs · Run semantic search · Review evidence pages")
st.divider()

# --- ZIP upload ---
st.subheader("📦 Vendor Documents")
uploaded_files = st.file_uploader(
    "Upload one or more vendor ZIP files",
    type=["zip"],
    accept_multiple_files=True,
    help="Each ZIP should contain the vendor's submitted PDF documents",
)

if not uploaded_files:
    st.info("👆 Upload vendor ZIP file(s) to begin. Edit and save rules in the sidebar first.")
    st.stop()

st.success(f"{len(uploaded_files)} ZIP file(s) ready: {', '.join(f.name for f in uploaded_files)}")

# --- Run button ---
st.divider()
run_clicked = st.button("🚀 Run Semantic Search", type="primary", use_container_width=True)

# ── PIPELINE — only executes when Run is clicked ────────────────────────────────
# Previously: any widget interaction (dropdown change, snippet expand) could
# silently re-run this block. Now: guarded by run_clicked so the pipeline
# runs ONLY on explicit button press. Results persist in session_state
# across all subsequent UI interactions.
if run_clicked:

    # --- Validate rules ---
    try:
        rules = load_rules(RULES_PATH)
    except (FileNotFoundError, ValueError) as e:
        st.error(f"❌ Rules error: {e}")
        st.stop()

    all_results = []
    all_logs = []
    failed = []

    progress_bar = st.progress(0, text="Starting...")
    status = st.empty()

    for idx, uploaded_file in enumerate(uploaded_files):
        vendor_name = Path(uploaded_file.name).stem
        progress_val = int((idx / len(uploaded_files)) * 90)
        progress_bar.progress(progress_val, text=f"Processing {uploaded_file.name}...")
        status.info(f"[{idx+1}/{len(uploaded_files)}] Processing: {uploaded_file.name}")

        tmp_zip = Path(tempfile.mktemp(suffix=".zip"))
        tmp_zip.write_bytes(uploaded_file.read())

        try:
            results, run_log = run_pipeline(str(tmp_zip), rules, top_n=int(top_n))
            for r in results:
                r["vendor_id"] = vendor_name
            all_results.extend(results)
            all_logs.append(f"\n{'='*40}\nVENDOR: {uploaded_file.name}\n{'='*40}")
            all_logs.extend(run_log)
        except Exception as e:
            failed.append(uploaded_file.name)
            st.warning(f"⚠️ Skipped {uploaded_file.name}: {e}")
            all_logs.append(f"FAILED: {uploaded_file.name} — {e}")
        finally:
            tmp_zip.unlink(missing_ok=True)

    progress_bar.progress(95, text="Writing outputs...")

    if not all_results:
        st.error("❌ No results generated. Check your ZIP files and rules.")
        st.stop()

    # --- Save outputs ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_path = write_excel(all_results, str(OUTPUT_DIR))

    log_path = OUTPUT_DIR / f"SyDRe_RunLog_{timestamp}.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"SyDRe Run Log — {timestamp}\n{'='*60}\n\n")
        f.write("\n".join(all_logs))

    progress_bar.progress(100, text="Done!")
    status.success(f"✅ Complete — {len(all_results)} results across {len(uploaded_files) - len(failed)} vendor(s)")

    # ── Store everything in session_state ───────────────────────────────────────
    # From this point on, all display code reads from session_state —
    # never from a fresh pipeline run.
    st.session_state.results = all_results
    st.session_state.excel_path = excel_path
    st.session_state.run_logs = all_logs
    st.session_state.last_run_summary = (
        f"✅ {len(all_results)} results · "
        f"{len(uploaded_files) - len(failed)} vendor(s) · "
        f"{timestamp}"
    )

# ── Results display — reads from session_state, never re-runs pipeline ──────────
if not st.session_state.results:
    st.stop()

st.divider()

# Show last run summary so auditor knows what they're looking at
if st.session_state.last_run_summary:
    st.caption(f"Last run: {st.session_state.last_run_summary}")

st.subheader("📊 Results")

df = pd.DataFrame(st.session_state.results)

# --- Vendor filter ---
vendors = sorted(df["vendor_id"].unique())
if len(vendors) > 1:
    selected_vendor = st.selectbox("Filter by vendor:", ["All vendors"] + vendors)
    if selected_vendor != "All vendors":
        df = df[df["vendor_id"] == selected_vendor]

# --- Rule filter ---
rule_options = sorted(df["rule_id"].unique())
selected_rule = st.selectbox("Filter by rule:", ["All rules"] + rule_options)
if selected_rule != "All rules":
    df = df[df["rule_id"] == selected_rule]

# --- Score colour coding ---
def colour_score(val):
    if isinstance(val, float):
        if val >= 0.8:
            return "background-color: #C6EFCE; color: #276221"
        elif val >= 0.6:
            return "background-color: #FFEB9C; color: #9C5700"
        else:
            return "background-color: #FFC7CE; color: #9C0006"
    return ""

display_cols = ["vendor_id", "rule_id", "rule_text", "rank",
                "file_name", "page_number", "score", "source_type"]
df_display = df[display_cols].copy()
df_display.columns = ["Vendor", "Rule ID", "Rule Text", "Rank",
                       "File", "Page", "Score", "Source"]

styled = df_display.style.map(colour_score, subset=["Score"])
st.dataframe(styled, use_container_width=True, height=500)

# --- Score legend ---
col1, col2, col3 = st.columns(3)
col1.markdown("🟢 **≥ 0.80** — Strong match")
col2.markdown("🟡 **0.60–0.79** — Moderate match")
col3.markdown("🔴 **< 0.60** — Weak match")

# --- Text snippets ---
st.divider()
st.subheader("📄 Page Text Snippets")
st.caption("Expand a result to read the extracted page text")

for _, row in df.iterrows():
    label = f"{row['vendor_id']} · {row['rule_id']} · Rank {row['rank']} · {row['file_name']} Pg {row['page_number']} · Score {row['score']}"
    with st.expander(label):
        source_badge = "🔵 OCR" if "OCR" in str(row.get("source_type", "")) else "⚪ Native"
        st.caption(source_badge)
        st.text(row.get("snippet", "(no text)"))

# --- Run log ---
if st.session_state.run_logs:
    st.divider()
    with st.expander("📋 View Run Log"):
        st.text("\n".join(st.session_state.run_logs))

# --- Download ---
st.divider()
if st.session_state.excel_path:
    with open(st.session_state.excel_path, "rb") as f:
        excel_bytes = f.read()

    st.download_button(
        label="⬇️ Download Excel Results",
        data=excel_bytes,
        file_name=Path(st.session_state.excel_path).name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )
    st.caption(f"Excel saved to: `{st.session_state.excel_path}`")