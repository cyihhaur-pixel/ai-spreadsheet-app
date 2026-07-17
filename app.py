import streamlit as st
import pandas as pd
import json, os, io, zipfile
from datetime import datetime
from groq import Groq
from pypdf import PdfReader, PdfWriter

st.set_page_config(page_title="Bulk Requisition Pro", layout="wide")
st.title("🚀 Bulk Requisition Pro")

api_key = st.sidebar.text_input("Groq API Key:", type="password")
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])

# Input
raw_text = st.text_area("Paste invoice details here:", height=200)

if st.button("⚡ Process & Add to Batch"):
    if not api_key: st.error("Need API Key"); st.stop()
    client = Groq(api_key=api_key)
    system_prompt = (
        "Extract to JSON: Company, Payee, Amount, Invoice_No, Release_date.\n"
        "1. Company: Exact keywords only: venture, putra, pyramid, top, mm, mytown, sp, aman, ct, imago, kuching, bintulu, miri.\n"
        "2. Payee: Return in ALL CAPS.\n"
        "3. Amount: Format as '5,000.00' (with comma, two decimals).\n"
        "4. Release_date: Must be: '1st of the month', '7th of the month', '15th of the month', or 'Urgent'."
    )
    res = client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
        model="llama-3.3-70b-versatile", response_format={"type": "json_object"}
    )
    data = json.loads(res.choices[0].message.content)
    data["Company"] = data["Company"].upper()
    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([data])], ignore_index=True)
    st.rerun()

st.dataframe(st.session_state.df, use_container_width=True)

if not st.session_state.df.empty:
    col1, col2 = st.columns(2)
    # Excel Export
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
        st.session_state.df.to_excel(writer, index=False)
    col1.download_button("📥 Download Master Log", excel_io.getvalue(), "requisitions.xlsx")
    
    # Bulk PDF Export
    if col2.button("📦 Generate Bulk PDFs"):
        if not os.path.exists("template.pdf"): st.error("template.pdf missing!"); st.stop()
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, 'w') as zf:
            for _, row in st.session_state.df.iterrows():
                writer = PdfWriter(); writer.append(PdfReader("template.pdf"))
                form_data = {"txt_date": datetime.now().strftime("%d-%m-%Y"), "txt_payee": row["Payee"], 
                             "txt_amount": row["Amount"], "txt_invoice": row["Invoice_No"]}
                
                # Checkbox Logic
                comp = row["Company"].lower()
                mapping = {"venture":"Parenthood Venture SB", "putra":"Parenthood Playground SB (Putra)", "pyramid":"Parenthood Playground SB (Pyramid)", 
                           "top":"Parenthood TOP SB", "mm":"Parenthood MM SB", "mytown":"Parenthood My Town SB", "sp":"Parenthood SP SB", 
                           "aman":"Parenthood Aman SB", "ct":"Parenthood CT SB", "imago":"Parenthood YB SB (Imago)", 
                           "kuching":"Parenthood KBM SB (Kuching)", "bintulu":"Parenthood KBM SB (Bintulu)", "miri":"Parenthood KBM SB (Miri)"}
                if comp in mapping: form_data[mapping[comp]] = "/Yes"
                form_data[row["Release_date"]] = "/Yes"
                
                writer.update_page_form_field_values(writer.pages[0], form_data)
                writer.set_need_appearances_writer()
                pdf_io = io.BytesIO(); writer.write(pdf_io)
                zf.writestr(f"req_{row['Invoice_No']}.pdf", pdf_io.getvalue())
        col2.download_button("💾 Download ZIP", zip_io.getvalue(), "requisitions.zip")

if st.button("🗑️ Reset All"):
    st.session_state.df = pd.DataFrame(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])
    st.rerun()
