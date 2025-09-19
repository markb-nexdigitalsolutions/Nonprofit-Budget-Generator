import io
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


# -----------------------------
# Helpers
# -----------------------------
def money(x):
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return x

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def make_federal_pdf(org_name: str, program_title: str, df: pd.DataFrame) -> bytes:
    """
    Very simple tabular PDF export for the Federal (SF-424A style) table.
    """
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

    # headers
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

def sample_operating_df():
    return pd.DataFrame([
        {"Category": "Personnel (Salaries)", "Amount": 450000, "Percentage": 60},
        {"Category": "Fringe Benefits", "Amount": 135000, "Percentage": 18},
        {"Category": "Program Supplies", "Amount": 45000, "Percentage": 6},
        {"Category": "Equipment", "Amount": 30000, "Percentage": 4},
        {"Category": "Travel", "Amount": 15000, "Percentage": 2},
        {"Category": "Communications", "Amount": 12000, "Percentage": 1.6},
        {"Category": "Utilities", "Amount": 18000, "Percentage": 2.4},
        {"Category": "Rent/Facilities", "Amount": 60000, "Percentage": 8},
        {"Category": "Administrative Costs", "Amount": 75000, "Percentage": 10},
    ])

def sample_program_df():
    return pd.DataFrame([
        {"Line Item": "Program Director (1.0 FTE)", "Units": 12, "Unit Cost": 6500, "Total": 78000},
        {"Line Item": "Case Managers (2.0 FTE)", "Units": 24, "Unit Cost": 4200, "Total": 100800},
        {"Line Item": "Administrative Assistant (0.5 FTE)", "Units": 6, "Unit Cost": 3000, "Total": 18000},
        {"Line Item": "Fringe Benefits (30%)", "Units": 1, "Unit Cost": 59040, "Total": 59040},
        {"Line Item": "Program Materials", "Units": 200, "Unit Cost": 75, "Total": 15000},
        {"Line Item": "Client Transportation", "Units": 500, "Unit Cost": 25, "Total": 12500},
        {"Line Item": "Training & Professional Development", "Units": 4, "Unit Cost": 1250, "Total": 5000},
        {"Line Item": "Office Supplies", "Units": 12, "Unit Cost": 400, "Total": 4800},
        {"Line Item": "Communications", "Units": 12, "Unit Cost": 200, "Total": 2400},
        {"Line Item": "Indirect Costs (10%)", "Units": 1, "Unit Cost": 29554, "Total": 29554},
    ])

def sample_federal_df():
    return pd.DataFrame([
        {"Budget Category": "Personnel", "Federal Share": 196800, "Non-Federal Share": 0, "Total": 196800},
        {"Budget Category": "Fringe Benefits", "Federal Share": 59040, "Non-Federal Share": 0, "Total": 59040},
        {"Budget Category": "Travel", "Federal Share": 12500, "Non-Federal Share": 0, "Total": 12500},
        {"Budget Category": "Equipment", "Federal Share": 0, "Non-Federal Share": 0, "Total": 0},
        {"Budget Category": "Supplies", "Federal Share": 19800, "Non-Federal Share": 0, "Total": 19800},
        {"Budget Category": "Contractual", "Federal Share": 0, "Non-Federal Share": 0, "Total": 0},
        {"Budget Category": "Other", "Federal Share": 2400, "Non-Federal Share": 0, "Total": 2400},
        {"Budget Category": "Total Direct Costs", "Federal Share": 290540, "Non-Federal Share": 0, "Total": 290540},
        {"Budget Category": "Indirect Costs (10%)", "Federal Share": 29054, "Non-Federal Share": 0, "Total": 29054},
        {"Budget Category": "TOTAL PROJECT COSTS", "Federal Share": 319594, "Non-Federal Share": 0, "Total": 319594},
    ])


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="Nonprofit Budget Generator", page_icon="📊", layout="wide")

st.markdown(
    """
    <div style="padding: 1.8rem; border-radius: 16px;
         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
      <h1 style="margin:0;">Nonprofit Budget Generator</h1>
      <p style="margin-top:.4rem; opacity:.95;">Transform your program documents into comprehensive budget packages</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# --- Upload area (visual only for now — processing is simulated) ---
with st.expander("📎 Upload Program Documents (PDF)"):
    colU1, colU2 = st.columns(2)
    with colU1:
        prog_pdf = st.file_uploader("Program Design (PDF)", type=["pdf"])
    with colU2:
        need_pdf = st.file_uploader("Statement of Need (PDF)", type=["pdf"])

# --- Organization info ---
st.subheader("🏷️ Organization Information")
c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1])
with c1:
    org_name = st.text_input("Organization Name", placeholder="Enter organization name")
with c2:
    program_title = st.text_input("Program Title", placeholder="Enter program title")
with c3:
    grant_period = st.text_input("Grant Period", placeholder="e.g., 12 months")
with c4:
    total_request = st.number_input("Total Request Amount", min_value=0, step=1000)

# --- Process button ---
disabled = not (prog_pdf and need_pdf)
process = st.button("⚙️ Process Documents & Generate Budgets", disabled=disabled, use_container_width=True)

if process:
    with st.spinner("Processing documents and generating budgets…"):
        # Simulated extraction → seed with sample data
        st.session_state["operating_df"] = sample_operating_df()
        st.session_state["program_df"] = sample_program_df()
        st.session_state["federal_df"] = sample_federal_df()
    st.success("Budgets generated! Scroll to review and export.")

# --- Results ---
if "operating_df" in st.session_state:
    st.write("---")
    st.subheader("📊 Budgets")

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
        st.session_state["program_df"] = st.data_editor(
            st.session_state["program_df"],
            num_rows="dynamic",
            use_container_width=True
        )
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

    # Federal
    with tab3:
        st.caption("SF-424A-style categories. Totals update as you edit.")
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
