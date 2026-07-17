import streamlit as st
import pandas as pd
import json, io, zipfile
from datetime import datetime
from groq import Groq
from pypdf import PdfReader, PdfWriter

# Set page to wide mode for the best foldable tablet experience
st.set_page_config(page_title="Enterprise Requisition", layout="wide")
st.title("🏢 Enterprise Requisition System")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Groq API Key:", type="password")
    uploaded_template = st.file_uploader("Upload PDF Template", type="pdf")
    if st.button("Reset Session", width='stretch'):
        st.session_state.df = pd.DataFrame(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])
        st.rerun()

# Initialize session state
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])

# Form-based input to ensure reliable triggering on mobile/touch interfaces
st.subheader("Bulk Input")
with st.form("input_form", clear_on_submit=True):
    raw_text = st.text_area("Paste invoice data:", height=120, help="Format: Company - Payee - Amount - Invoice - Date")
    submitted = st.form_submit_button("⚡ Process & Validate Batch", type="primary", width='stretch')

if submitted:
    if not api_key:
        st.error("API Key required.")
    elif not raw_text.strip():
        st.warning("Please paste invoice data first.")
    else:
        client = Groq(api_key=api_key)
        with st.spinner("Processing data..."):
            try:
                res = client.chat.completions.create(
                    messages=[{"role": "system", "content": "Extract to JSON. Keys: Company, Payee, Amount, Invoice_No, Release_date. Clean data to corporate standard."}, 
                              {"role": "user", "content": raw_text}],
                    model="llama-3.3-70b-versatile", response_format={"type": "json_object"}
                )
                data = json.loads(res.choices[0].message.content)
                new_data = []
                for item in data.get("items", []):
                    new_data.append({
                        "Company": str(item.get("Company", "")).upper().strip(),
                        "Payee": str(item.get("Payee", "N/A")).upper().strip(),
                        "Amount": str(item.get("Amount", "RM 0.00")),
                        "Invoice_No": str(item.get("Invoice_No", "N/A")),
                        "Release_date": str(item.get("Release_date", "15th"))
                    })
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame(new_data)], ignore_index=True)
                st.rerun()
            except Exception as e:
                st.error(f"Processing Error: {e}")

# Editable data queue
st.subheader("Verification Queue")
st.session_state.df = st.data_editor(st.session_state.df, width='stretch', num_rows="dynamic")

# Final actions
if not st.session_state.df.empty:
    col1, col2 = st.columns(2)
    
    # Export Log
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io) as writer: st.session_state.df.to_excel(writer, index=False)
    col1.download_button("📊 Export Audit Log", excel_io.getvalue(), "log.xlsx", width='stretch')
    
    # PDF Generator
    if col2.button("🚀 Generate PDF Batch", width='stretch'):
        if not uploaded_template: st.error("Template required!"); st.stop()
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, 'w') as zf:
            for _, row in st.session_state.df.iterrows():
                writer = PdfWriter(); writer.append(PdfReader(uploaded_template))
                mapping = {"VENTURE":"Parenthood Venture SB", "PUTRA":"Parenthood Playground SB (Putra)", "PYRAMID":"Parenthood Playground SB (Pyramid)", "TOP":"Parenthood TOP SB", "MM":"Parenthood MM SB", "MYTOWN":"Parenthood My Town SB", "SP":"Parenthood SP SB", "AMAN":"Parenthood Aman SB", "CT":"Parenthood CT SB", "IMAGO":"Parenthood YB SB (Imago)", "KUCHING":"Parenthood KBM SB (Kuching)", "BINTULU":"Parenthood KBM SB (Bintulu)", "MIRI":"Parenthood KBM SB (Miri)"}
                
                form_data = {"txt_date": datetime.now().strftime("%d-%m-%Y"), "txt_payee": row["Payee"], "txt_amount": row["Amount"], "txt_invoice": row["Invoice_No"]}
                if row["Company"] in mapping: form_data[mapping[row["Company"]]] = "/Yes"
                form_data[row["Release_date"]] = "/Yes"
                
                writer.update_page_form_field_values(writer.pages[0], form_data)
                pdf_io = io.BytesIO(); writer.write(pdf_io)
                zf.writestr(f"{row['Company'] or 'GEN'}_{row['Invoice_No']}.pdf", pdf_io.getvalue())
        col2.download_button("💾 Download ZIP", zip_io.getvalue(), "requisitions.zip", width='stretch')
