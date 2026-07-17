import streamlit as st
import pandas as pd
import json, io, zipfile
from datetime import datetime
from groq import Groq
from pypdf import PdfReader, PdfWriter

# --- Configuration & Theme ---
st.set_page_config(page_title="Enterprise Requisition System", layout="wide")
st.title("🏢 Enterprise Requisition System")

# --- Authentication & Assets ---
with st.container():
    col_a, col_b = st.columns(2)
    api_key = col_a.text_input("Groq API Key:", type="password")
    uploaded_template = col_b.file_uploader("Upload Requisition Template (.pdf)", type="pdf")

# --- Persistent State ---
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])

# --- Processing Logic ---
st.subheader("Bulk Input")
raw_text = st.text_area("Paste invoice data (CSV/Text format):", height=120, help="Paste lines containing Company, Payee, Amount, Invoice#, Date.")

if st.button("⚡ Process & Validate Batch", use_container_width=True):
    if not api_key: st.error("API Key required."); st.stop()
    client = Groq(api_key=api_key)
    
    with st.spinner("Executing extraction..."):
        try:
            res = client.chat.completions.create(
                messages=[{"role": "system", "content": "Extract to JSON. Keys: Company, Payee, Amount, Invoice_No, Release_date. Clean data to standard corporate format."}, 
                          {"role": "user", "content": raw_text}],
                model="llama-3.3-70b-versatile", response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            
            # Data Normalization
            new_data = []
            for item in data.get("items", []):
                new_data.append({
                    "Company": str(item.get("Company", "")).upper().strip(),
                    "Payee": str(item.get("Payee", "N/A")).upper().strip(),
                    "Amount": str(item.get("Amount", "RM 0.00")),
                    "Invoice_No": str(item.get("Invoice_No", "N/A")),
                    "Release_date": str(item.get("Release_date", "15th of the month"))
                })
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame(new_data)], ignore_index=True)
            st.rerun()
        except Exception as e:
            st.error(f"Extraction Error: {e}")

# --- Editable Data Grid ---
st.subheader("Review & Finalize Data")
st.session_state.df = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic")

# --- Production Actions ---
if not st.session_state.df.empty:
    col1, col2, col3 = st.columns(3)
    
    # Export Log
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io) as writer: st.session_state.df.to_excel(writer, index=False)
    col1.download_button("📊 Export Audit Log", excel_io.getvalue(), f"Audit_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
    
    # Generate PDFs
    if col2.button("🚀 Generate PDF Pack", use_container_width=True):
        if not uploaded_template: st.error("Template missing."); st.stop()
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, 'w') as zf:
            for _, row in st.session_state.df.iterrows():
                writer = PdfWriter(); writer.append(PdfReader(uploaded_template))
                # Mapping Logic
                mapping = {"VENTURE":"Parenthood Venture SB", "PUTRA":"Parenthood Playground SB (Putra)", "PYRAMID":"Parenthood Playground SB (Pyramid)", "TOP":"Parenthood TOP SB", "MM":"Parenthood MM SB", "MYTOWN":"Parenthood My Town SB", "SP":"Parenthood SP SB", "AMAN":"Parenthood Aman SB", "CT":"Parenthood CT SB", "IMAGO":"Parenthood YB SB (Imago)", "KUCHING":"Parenthood KBM SB (Kuching)", "BINTULU":"Parenthood KBM SB (Bintulu)", "MIRI":"Parenthood KBM SB (Miri)"}
                form_data = {"txt_date": datetime.now().strftime("%d-%m-%Y"), "txt_payee": row["Payee"], "txt_amount": row["Amount"], "txt_invoice": row["Invoice_No"]}
                if row["Company"] in mapping: form_data[mapping[row["Company"]]] = "/Yes"
                form_data[row["Release_date"]] = "/Yes"
                writer.update_page_form_field_values(writer.pages[0], form_data)
                pdf_io = io.BytesIO(); writer.write(pdf_io)
                zf.writestr(f"{row['Company'] or 'GENERAL'}_{row['Invoice_No']}.pdf", pdf_io.getvalue())
        col3.download_button("💾 Download ZIP", zip_io.getvalue(), "Enterprise_Batch.zip", use_container_width=True)
