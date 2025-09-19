import io
import re
from collections import Counter
from datetime import datetime

import pandas as pd
import streamlit as st

# Optional for PDF export
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

# Optional for PDF text extraction
try:
    import PyPDF2
    HAS_PYPDF2 = True
except Exception:
    HAS_PYPDF2 = False


# -----------------------------
# Locality data (lightweight, built-in)
# -----------------------------
STATE_COST_INDEX = {
    "AL": 0.89, "AK": 1.15, "AZ": 0.97, "AR": 0.88, "CA": 1.22, "CO": 1.08, "CT": 1.17,
    "DE": 1.03, "FL": 0.98, "GA": 0.96, "HI": 1.35, "ID": 0.95, "IL": 1.07, "IN": 0.93,
    "IA": 0.92, "KS": 0.91, "KY": 0.90, "LA": 0.90, "ME": 1.02, "MD": 1.12, "MA": 1.18,
    "MI": 0.94, "MN": 1.03, "MS": 0.86, "MO": 0.92, "MT": 0.93, "NE": 0.92, "NV": 0.98,
    "NH": 1.05, "NJ": 1.18, "NM": 0.90, "NY": 1.25, "NC": 0.95, "ND": 0.92, "OH": 0.94,
    "OK": 0.89, "OR": 1.07, "PA": 0.99, "RI": 1.06, "SC": 0.93, "SD": 0.90, "TN": 0.92,
    "TX": 0.96, "UT": 1.02, "VT": 1.03, "VA": 1.05, "WA": 1.12, "WV": 0.88, "WI": 0.95,
    "WY": 0.92, "DC": 1.30,
}

CITY_OVERRIDES = {
    "New York": 1.45, "San Francisco": 1.50, "San Jose": 1.45, "San Diego": 1.28,
    "Los Angeles": 1.30, "Seattle": 1.25, "Washington": 1.35, "Boston": 1.30,
    "Chicago": 1.18, "Miami": 1.20, "Denver": 1.15, "Portland": 1.12, "Philadelphia": 1.08,
    "Baltimore": 1.05, "Austin": 1.08, "Las Vegas": 1.03, "Atlanta": 1.02,
    "Cleveland": 0.90, "Detroit": 0.92, "Columbus": 0.94, "Houston": 0.98, "Dallas": 1.00,
    "Charlotte": 0.99, "Phoenix": 0.99, "Jacksonville": 0.98
}

def resolve_locality_factor(city: str | None, state: str | None) -> float:
    if city:
        for key in CITY_OVERRIDES:
            if key.lower() == city.strip().lower():
                return CITY_OVERRIDES[key]
    if state:
        state = state.strip().upper()
        if state in STATE_COST_INDEX:
            return STATE_COST_INDEX[state]
    return 1.00


# -----------------------------
# PDF helpers
# -----------------------------
CITY_STATE_RE = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*)\s*,\s*([A-Z]{2})\b")

def extract_text_from_pdf(file) -> str:
    if not HAS_PYPDF2 or file is None:
        return ""
    try:
        reader = PyPDF2.PdfReader(file)
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(texts)
    except Exception:
        return ""

def find_city_state_from_text(text: str) -> tuple[str | None, str | None]:
    matches = CITY_STATE_RE.findall(text or "")
    if not matches:
        return (None, None)
    common = Counter(matches).most_common(1)[0][0]
    city, state = common[0], common[1]
    city = re.sub(r"^(City|County)\s+of\s+", "", city, flags=re.I).strip()
    return (city, state)


# -----------------------------
# Formatting helpers
# -----------------------------
def money(x):
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return x

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def make_federal_pdf(org_name: str, program_title: str, df: pd.DataFrame) -> bytes:
    if not HAS_REPORTLAB:
        return b""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    y = height - 1 * inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1 * inch, y, "Federal Grant Budget (SF-424A Format)")
    y -= 0.4 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, y, f"Organization: {org_name or 'Sample Nonprofit Organization'}")
    y -= 0.25 * inch
    c.drawString(1 * inch, y, f"Program: {program_title or 'Community Support Program'}")
    y -= 0.35 * inch

    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y, "Budget Category")
    c.drawRightString(4.1 * inch, y, "Federal Share")
    c.drawRightString(5.6 * inch, y, "Non-Federal Share")
    c.drawRightString(7.2 * inch, y, "Total")
    y -= 0.22 * inch
    c.line(1 * inch, y, 7.3 * inch, y)
    y -= 0.12 * inch

    c.setFont("Helvetica", 10)
    for _, r in df.iterrows():
        row_h = 0.22 * inch
        if y < 1 * inch:
            c.showPage()
            y = height - 1 * inch
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1 * inch, y, "Budget Category")
            c.drawRightString(4.1 * inch, y, "Federal Share")
            c.drawRightString(5.6 * inch, y, "Non-Federal Share")
            c.drawRightString(7.2 * inch, y, "Total")
            y -= 0.22 * inch
            c.line(1 * inch, y, 7.3 * inch, y)
            y -= 0.12 * inch
            c.setFont("Helvetica", 10)

        cat = str(r.get("Budget Category", ""))
        fed = money(r.get("Federal Share", 0))
        non = money(r.get("Non-Federal Share", 0))
        tot = money(r.get("Total", 0))

        c.drawString(1 * inch, y, cat[:60])
        c.drawRightString(4.1 * inch, y, fed)
        c.drawRightString(5.6 * inch, y, non)
        c.drawRightString(7.2 * inch, y, tot)
        y -= row_h

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# -----------------------------
# Budget generators (locality-aware)
# -----------------------------
def generate_program_df(locality: float) -> pd.DataFrame:
    sal_factor = locality
    other_factor = pow(locality, 0.85)

    pd_month = 6500 * sal_factor
    cm_month = 4200 * sal_factor
    admin_month = 3000 * sal_factor

    rows = [
        {"Line Item": "Program Director (1.0 FTE)", "Units": 12, "Unit Cost": round(pd_month, 2)},
        {"Line Item": "Case Managers (2.0 FTE)", "Units": 24, "Unit Cost": round(cm_month, 2)},
        {"Line Item": "Administrative Assistant (0.5 FTE)", "Units": 6, "Unit Cost": round(admin_month, 2)},
        {"Line Item": "Program Materials", "Units": 200, "Unit Cost": round(75 * other_factor, 2)},
        {"Line Item": "Client Transportation", "Units": 500, "Unit Cost": round(25 * other_factor, 2)},
        {"Line Item": "Training & Professional Development", "Units": 4, "Unit Cost": round(1250 * other_factor, 2)},
        {"Line Item": "Office Supplies", "Units": 12, "Unit Cost": round(400 * other_factor, 2)},
        {"Line Item": "Communications", "Units": 12, "Unit Cost": round(200 * other_factor, 2)},
    ]
    df = pd.DataFrame(rows)
    df["Total"] = (df["Units"] * df["Unit Cost"]).round(2)

    salary_total = df.loc[df["Line Item"].str.contains("FTE", na=False), "Total"].sum()
    benefits = round(0.30 * salary_total, 2)
    df = pd.concat([df, pd.DataFrame([{
        "Line Item": "Fringe Benefits (30%)", "Units": 1, "Unit Cost": benefits, "Total": benefits
    }])], ignore_index=True)

    subtotal = df["Total"].sum()
    indirect = round(0.10 * subtotal, 2)
    df = pd.concat([df, pd.DataFrame([{
        "Line Item": "Indirect Costs (10%)", "Units": 1, "Unit Cost": indirect, "Total": indirect
    }])], ignore_index=True)

    return df


def generate_operating_df(locality: float) -> pd.DataFrame:
    sal_factor = locality
    rent_factor = pow(locality, 1.1)
    util_factor = pow(locality, 0.9)
    other_factor = pow(locality, 0.85)

    baseline = {
        "Personnel (Salaries)": 450000 * sal_factor,
        "Fringe Benefits": 135000 * sal_factor,
        "Program Supplies": 45000 * other_factor,
        "Equipment": 30000 * other_factor,
        "Travel": 15000 * other_factor,
        "Communications": 12000 * other_factor,
        "Utilities": 18000 * util_factor,
        "Rent/Facilities": 60000 * rent_factor,
        "Administrative Costs": 75000 * other_factor,
    }

    total = sum(baseline.values())
    df = pd.DataFrame(
        [{"Category": k, "Amount": round(v, 2), "Percentage": round(100 * v / total, 1)} for k, v in baseline.items()]
    )
    return df


# -----------------------------
# Match / Cost Share helpers
# -----------------------------
def split_match(total_cost: float, value: float, mode: str = "percent_of_total"):
    """
    mode: 'percent_of_total' (value = % of total, e.g., 0.25)
          'percent_of_federal' (value = % of federal, e.g., 0.20)
    Returns (federal, match, total)
    """
    if total_cost <= 0:
        return 0.0, 0.0, 0.0

    if mode == "percent_of_total":
        match_amt = total_cost * value
        federal = total_cost - match_amt
        return round(federal, 2), round(match_amt, 2), round(total_cost, 2)
    elif mode == "percent_of_federal":
        federal = total_cost / (1 + value)
        match_amt = federal * value
        return round(federal, 2), round(match_amt, 2), round(total_cost, 2)
    else:
        raise ValueError("mode must be 'percent_of_total' or 'percent_of_federal'")


def allocate_shares(detail_totals: pd.Series, federal_total: float, match_total: float) -> tuple[pd.Series, pd.Series]:
    """
    Proportionally allocate federal and match across detail rows (by Total).
    Returns (federal_shares, match_shares) aligned to detail_totals index.
    """
    base = detail_totals.clip(lower=0.0).astype(float)
    s = float(base.sum())
    if s <= 0:
        return pd.Series(0.0, index=detail_totals.index), pd.Series(0.0, index=detail_totals.index)

    fed = (base / s) * federal_total
    mat = (base / s) * match_total

    # Fix rounding drift on the last item
    fed = fed.round(2)
    mat = mat.round(2)
    if len(fed) > 0:
        fed.iloc[-1] += round(federal_total - float(fed.sum()), 2)
        mat.iloc[-1] += round(match_total - float(mat.sum()), 2)
    return fed, mat


def generate_federal_df(program_df: pd.DataFrame,
                        match_mode: str,
                        match_percent: float,
                        use_total_request: bool,
                        total_request: float,
                        interpret_total_request_as: str):
    """
    Build SF-424A-like table and split Federal vs. Non-Federal using match rules.
    - If use_total_request:
        * 'federal'  -> treat Total Request as the Federal share target
        * 'total'    -> treat Total Request as the Total Project Cost
      The match_percent still defines the relationship (mode).
    - Else: base on Program Budget total as Total Project Cost.
    """
    # 1) Map program_df -> SF-424A categories (as totals first)
    def cat_total(keyword_list):
        mask = pd.Series(False, index=program_df.index)
        for kw in keyword_list:
            mask |= program_df["Line Item"].str.contains(kw, case=False, na=False)
        return float(program_df.loc[mask, "Total"].sum())

    personnel = cat_total(["FTE", "Director", "Manager", "Assistant"])
    fringe = cat_total(["Fringe"])
    travel = cat_total(["Travel", "Transportation"])
    equipment = cat_total(["Equipment"])
    supplies = cat_total(["Materials", "Supplies"])
    contractual = 0.0
    other = cat_total(["Communications", "Training", "Indirect"])

    detail_rows = pd.DataFrame([
        {"Budget Category": "Personnel", "Total": personnel},
        {"Budget Category": "Fringe Benefits", "Total": fringe},
        {"Budget Category": "Travel", "Total": travel},
        {"Budget Category": "Equipment", "Total": equipment},
        {"Budget Category": "Supplies", "Total": supplies},
        {"Budget Category": "Contractual", "Total": contractual},
        {"Budget Category": "Other", "Total": other},
    ])

    total_project_cost = float(program_df["Total"].sum())

    # 2) Optionally override using Total Request field
    federal_target = None
    if use_total_request and total_request > 0:
        if interpret_total_request_as == "federal":
            # We have the federal share; back out total if needed by match rule.
            if match_mode == "percent_of_total":
                # federal = total * (1 - m)  -> total = federal / (1 - m)
                denom = max(1 - match_percent, 0.0001)
                total_project_cost = round(total_request / denom, 2)
                federal_target = round(total_request, 2)
            else:  # percent_of_federal
                # total = federal * (1 + m)
                total_project_cost = round(total_request * (1 + match_percent), 2)
                federal_target = round(total_request, 2)
        else:  # interpret as total project cost
            total_project_cost = round(total_request, 2)
            federal_target = None  # will be derived from split_match

    # 3) Compute federal/match totals
    if federal_target is not None:
        # Derive match from total & federal target
        match_total = round(total_project_cost - federal_target, 2)
        federal_total = round(federal_target, 2)
    else:
        federal_total, match_total, _ = split_match(
            total_cost=total_project_cost,
            value=match_percent,
            mode=match_mode
        )

    # 4) Allocate across detail categories proportionally
    fed_alloc, match_alloc = allocate_shares(detail_rows["Total"], federal_total, match_total)
    detail_rows["Federal Share"] = fed_alloc
    detail_rows["Non-Federal Share"] = match_alloc

    # Recompute detail totals per row for clarity
    detail_rows["Total"] = (detail_rows["Federal Share"] + detail_rows["Non-Federal Share"]).round(2)

    # 5) Add rollups
    direct_fed = float(detail_rows["Federal Share"].sum())
    direct_match = float(detail_rows["Non-Federal Share"].sum())
    direct_total = float(detail_rows["Total"].sum())

    df = detail_rows.copy()

    df = pd.concat([
        df,
        pd.DataFrame([{
            "Budget Category": "Total Direct Costs",
            "Federal Share": round(direct_fed, 2),
            "Non-Federal Share": round(direct_match, 2),
            "Total": round(direct_total, 2)
        }])
    ], ignore_index=True)

    # If your program_df has an "Indirect Costs" line, include it proportionally in "Other" above.
    # Alternatively, show a separate Indirect line with the same split proportion as 'Other':
    indirect_guess = float(program_df.loc[
        program_df["Line Item"].str.contains("Indirect", case=False, na=False), "Total"
    ].sum())

    if indirect_guess > 0:
        # Split indirect in the same ratio as the overall federal/match
        total_for_ratio = max(direct_total, 0.0001)
        fed_ratio = direct_fed / total_for_ratio
        ind_fed = round(indirect_guess * fed_ratio, 2)
        ind_match = round(indirect_guess - ind_fed, 2)
        df = pd.concat([
            df,
            pd.DataFrame([{
                "Budget Category": "Indirect Costs",
                "Federal Share": ind_fed,
                "Non-Federal Share": ind_match,
                "Total": round(ind_fed + ind_match, 2)
            }])
        ], ignore_index=True)

    # Grand total
    g_fed = float(df["Federal Share"].sum())
    g_match = float(df["Non-Federal Share"].sum())
    g_tot = float(df["Total"].sum())

    df = pd.concat([
        df,
        pd.DataFrame([{
            "Budget Category": "TOTAL PROJECT COSTS",
            "Federal Share": round(g_fed, 2),
            "Non-Federal Share": round(g_match, 2),
            "Total": round(g_tot, 2)
        }])
    ], ignore_index=True)

    # Ensure display order
    return df[["Budget Category", "Federal Share", "Non-Federal Share", "Total"]]


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="Nonprofit Budget Generator", page_icon="📊", layout="wide")

st.markdown(
    """
    <div style="padding: 1.8rem; border-radius: 16px;
         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
      <h1 style="margin:0;">Nonprofit Budget Generator</h1>
      <p style="margin-top:.4rem; opacity:.95;">Transform your program documents into comprehensive, locality-aware budget packages</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

with st.expander("📎 Upload Program Documents (PDF)"):
    colU1, colU2 = st.columns(2)
    with colU1:
        prog_pdf = st.file_uploader("Program Design (PDF)", type=["pdf"])
    with colU2:
        need_pdf = st.file_uploader("Statement of Need (PDF)", type=["pdf"])

# --- Try to detect city/state from PDFs ---
detected_city = None
detected_state = None
detected_factor = 1.00

if prog_pdf or need_pdf:
    text_blob = ""
    if prog_pdf:
        text_blob += "\n" + extract_text_from_pdf(prog_pdf)
        prog_pdf.seek(0)
    if need_pdf:
        text_blob += "\n" + extract_text_from_pdf(need_pdf)
        need_pdf.seek(0)
    c, s = find_city_state_from_text(text_blob)
    detected_city, detected_state = c, s
    detected_factor = resolve_locality_factor(detected_city, detected_state)

# --- Organization info ---
st.subheader("🏷️ Organization Information")
c1, c2, c3, c4 = st.columns([1.3, 1.3, 1, 1])
with c1:
    org_name = st.text_input("Organization Name", placeholder="Enter organization name")
with c2:
    program_title = st.text_input("Program Title", placeholder="Enter program title")
with c3:
    grant_period = st.text_input("Grant Period", placeholder="e.g., 12 months")
with c4:
    total_request = st.number_input("Total Request Amount (optional)", min_value=0, step=1000)

# --- Locality review / override ---
st.subheader("🌎 Locality Detection")
lc1, lc2, lc3 = st.columns([1.2, 0.6, 0.6])
with lc1:
    city_input = st.text_input("City (auto-detected from PDFs if possible)", value=detected_city or "")
with lc2:
    state_input = st.text_input("State (2-letter, e.g., OH)", value=detected_state or "")
with lc3:
    factor_override = st.number_input(
        "Locality Factor (1.00 = US average)",
        min_value=0.5, max_value=2.0, step=0.01,
        value=resolve_locality_factor(city_input, state_input) if (city_input or state_input) else detected_factor
    )
st.caption(
    "We scale salaries most with locality, rent/utilities moderately, and supplies slightly. "
    "Override the factor if you have specific internal benchmarks."
)

# --- Match / Cost Share UI ---
st.subheader("🤝 Match / Cost Share")
mc1, mc2, mc3 = st.columns([1.2, 0.8, 1.2])
with mc1:
    match_mode_label = st.selectbox(
        "Rule",
        ["Percent of Total Project Cost", "Percent of Federal Share"],
        index=0
    )
    match_mode = "percent_of_total" if match_mode_label.startswith("Percent of Total") else "percent_of_federal"
with mc2:
    match_percent_input = st.number_input("Match %", min_value=0.0, max_value=100.0, value=25.0, step=1.0)
    match_percent = match_percent_input / 100.0
with mc3:
    use_tr = st.checkbox("Use Total Request to back-calculate shares", value=False)

if use_tr:
    interp = st.radio(
        "Treat Total Request Amount as…",
        ["Federal Share", "Total Project Cost"],
        horizontal=True,
        index=0
    )
    interpret_total_request_as = "federal" if interp == "Federal Share" else "total"
else:
    interpret_total_request_as = "total"  # default path; we’ll base on Program Budget total

# --- Process button ---
disabled = not (prog_pdf and need_pdf)
process = st.button("⚙️ Process Documents & Generate Budgets", disabled=disabled, use_container_width=True)

if process:
    with st.spinner("Processing documents, applying locality & match rules, and generating budgets…"):
        program_df = generate_program_df(factor_override)
        operating_df = generate_operating_df(factor_override)
        federal_df = generate_federal_df(
            program_df=program_df,
            match_mode=match_mode,
            match_percent=match_percent,
            use_total_request=use_tr and total_request > 0,
            total_request=float(total_request or 0),
            interpret_total_request_as=interpret_total_request_as
        )

        st.session_state["operating_df"] = operating_df
        st.session_state["program_df"] = program_df
        st.session_state["federal_df"] = federal_df
        st.session_state["detected_city"] = city_input or detected_city
        st.session_state["detected_state"] = state_input or detected_state
        st.session_state["locality_factor"] = factor_override
        st.session_state["match_mode"] = match_mode
        st.session_state["match_percent"] = match_percent
        st.session_state["used_total_request"] = use_tr
        st.session_state["interpret_total_request_as"] = interpret_total_request_as

    st.success("Budgets generated! Scroll to review and export.")

# --- Results ---
if "operating_df" in st.session_state:
    st.write("---")
    st.subheader("📊 Budgets")

    info_city = st.session_state.get("detected_city") or "(not set)"
    info_state = st.session_state.get("detected_state") or "(not set)"
    info_factor = st.session_state.get("locality_factor", 1.0)

    # Derive match summary from the current federal_df
    fdf = st.session_state["federal_df"]
    g_row = fdf.loc[fdf["Budget Category"] == "TOTAL PROJECT COSTS"].iloc[0]
    fed_sum = float(g_row["Federal Share"])
    match_sum = float(g_row["Non-Federal Share"])
    total_sum = float(g_row["Total"])

    st.info(
        f"Applied Locality → City: **{info_city}**, State: **{info_state}**, Factor: **{info_factor:.2f}**  \n"
        f"Match Rule: **{'% of Total' if st.session_state.get('match_mode')=='percent_of_total' else '% of Federal'}** at "
        f"**{100*st.session_state.get('match_percent',0):.0f}%**  • "
        f"Federal: **{money(fed_sum)}**, Match: **{money(match_sum)}**, Total: **{money(total_sum)}**"
    )

    tab1, tab2, tab3 = st.tabs([
        "Annual Operating Budget",
        "Program Budget",
        "Federal Grant Budget (SF-424A)"
    ])

    # Operating
    with tab1:
        st.caption("Edit any cell below. Download updated CSV anytime.")
        st.session_state["operating_df"] = st.data_editor(
            st.session_state["operating_df"],
            num_rows="dynamic",
            use_container_width=True
        )
        colA, colB = st.columns([1, 2])
        with colA:
            total_oper = st.session_state["operating_df"]["Amount"].sum()
            st.metric("Total Annual Operating", money(total_oper))
        with colB:
            st.download_button(
                "⬇️ Download Operating Budget (CSV)",
                data=df_to_csv_bytes(st.session_state["operating_df"]),
                file_name="operating_budget.csv",
                mime="text/csv",
                use_container_width=True
            )

    # Program
    with tab2:
        st.caption("Units × Unit Cost should equal Total; you can adjust all three as needed.")
        edited = st.data_editor(
            st.session_state["program_df"],
            num_rows="dynamic",
            use_container_width=True
        )
        if {"Units", "Unit Cost"}.issubset(edited.columns):
            edited["Total"] = (edited["Units"] * edited["Unit Cost"]).round(2)
        st.session_state["program_df"] = edited

        total_prog = st.session_state["program_df"]["Total"].sum()
        colA, colB = st.columns([1, 2])
        with colA:
            st.metric("Total Program Budget", money(total_prog))
        with colB:
            st.download_button(
                "⬇️ Download Program Budget (CSV)",
                data=df_to_csv_bytes(st.session_state["program_df"]),
                file_name="program_budget.csv",
                mime="text/csv",
                use_container_width=True
            )

    # Federal (SF-424A)
    with tab3:
        st.caption("Federal vs. Match are allocated proportionally across categories. Edit cells if your funder requires a different spread.")
        st.session_state["federal_df"] = st.data_editor(
            st.session_state["federal_df"],
            num_rows="dynamic",
            use_container_width=True
        )
        f = st.session_state["federal_df"]
        total_fed = f["Federal Share"].sum()
        total_non = f["Non-Federal Share"].sum()
        total_all = f["Total"].sum()
        cF1, cF2, cF3 = st.columns(3)
        with cF1: st.metric("Federal Share (sum)", money(total_fed))
        with cF2: st.metric("Non-Federal Share (sum)", money(total_non))
        with cF3: st.metric("Total (sum)", money(total_all))

        colPDF, colCSV = st.columns(2)
        with colCSV:
            st.download_button(
                "⬇️ Download Federal Budget (CSV)",
                data=df_to_csv_bytes(f),
                file_name="federal_budget.csv",
                mime="text/csv",
                use_container_width=True
            )
        with colPDF:
            if HAS_REPORTLAB:
                pdf_bytes = make_federal_pdf(org_name, program_title, f)
                st.download_button(
                    "🧾 Download Federal Budget (PDF)",
                    data=pdf_bytes,
                    file_name="federal_budget_sf424a.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.info("Install `reportlab` to enable PDF export (already listed in requirements).")

    # Summary tiles
    st.write("")
    st.subheader("📌 Budget Summary")
    total_oper = st.session_state["operating_df"]["Amount"].sum()
    total_prog = st.session_state["program_df"]["Total"].sum()
    f = st.session_state["federal_df"]
    total_fed_req = f.loc[f["Budget Category"].str.contains("TOTAL PROJECT", case=False, na=False), "Total"]
    total_fed_req = float(total_fed_req.iloc[0]) if len(total_fed_req) else f["Federal Share"].sum()

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f"<div style='text-align:center;padding:16px;border-radius:12px;background:#eff6ff;'>"
            f"<div style='font-size:1.6rem;font-weight:700;color:#2563eb;'>{money(total_oper)}</div>"
            f"<div style='color:#1f2937;'>Annual Operating</div></div>", unsafe_allow_html=True
        )
    with s2:
        st.markdown(
            f"<div style='text-align:center;padding:16px;border-radius:12px;background:#ecfdf5;'>"
            f"<div style='font-size:1.6rem;font-weight:700;color:#059669;'>{money(total_prog)}</div>"
            f"<div style='color:#1f2937;'>Program Budget</div></div>", unsafe_allow_html=True
        )
    with s3:
        st.markdown(
            f"<div style='text-align:center;padding:16px;border-radius:12px;background:#f5f3ff;'>"
            f"<div style='font-size:1.6rem;font-weight:700;color:#7c3aed;'>{money(total_fed_req)}</div>"
            f"<div style='color:#1f2937;'>Federal Request</div></div>", unsafe_allow_html=True
        )

# Footer
st.write("")
st.caption(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} • Nonprofit Budget Generator")
