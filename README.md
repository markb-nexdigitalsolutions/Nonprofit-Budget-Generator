# 📊 Nonprofit Budget Generator

Convert program docs into editable, exportable nonprofit budgets (Operating, Program, and SF-424A-style Federal).  
Converted from an HTML prototype to Streamlit for easy deployment and CSV/PDF exports.

## ✨ Features
- Upload **Program Design** and **Statement of Need** (PDFs)
- Auto-generate sample budgets you can **edit inline**
- One-click **CSV downloads** for each budget
- **PDF export** for the Federal (SF-424A-style) table
- Clean summary tiles for quick totals

> Note: This version simulates extraction from PDFs and seeds sample rows for rapid iteration. Hook in your own extraction/logic later.

---

## 🚀 Run locally

```bash
git clone https://github.com/<your-username>/nonprofit-budget-generator.git
cd nonprofit-budget-generator
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
