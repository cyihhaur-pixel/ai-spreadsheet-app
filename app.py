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

raw_text = st.text_area("Paste ALL invoice details here:", height=200)

if st.button("⚡ Process & Add to Batch"):
    if not api_key: st.error("Need API Key"); st.stop()
    client = Groq(api_key=api_key)
    
    system_prompt = (
        "Extract payment items into JSON. Return an object with key 'items' (a list). "
        "Each object: \n"
        "- Company: Map to internal keyword: venture, putra, pyramid, top, mm, mytown, sp, aman, ct, imago, kuching, bintulu, or miri.\n"
        "- Payee: Extract full name. MUST expand abbreviations: 'ent' -> 'ENTERPRISE', 's/b' -> 'SDN BHD', 'co' -> 'COMPANY'. Return in ALL CAPS.\n"
        "- Amount: Format as 'RM 5,000.00' (with 'RM' prefix, comma, and two decimals).\n"
        "- Invoice_No: Extract clearly.\n"
        "- Release_date: Must be: '1st of the month', '7th of the month', '15th of the month', or 'Urgent'."
    )
    
    res = client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
        model="llama-3.3-70b-versatile", response_format={"type": "json_object"}
    )
    
    response_data = json.loads(res.choices[0].message.content)
    
    for item in response_data.get("items", []):
        new_row = pd.DataFrame([{
            "Company": str(item.get("Company", "N/A")).upper(),
            "Payee": str(item.get("Payee", "N/A")).upper(),
            "Amount": str(item.get("Amount", "RM 0.00")),
            "Invoice_No": str(item.get("Invoice_No", "N/A")),
            "Release_date": str(item.get("Release_date", "Urgent"))
        }])
        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
    st.rerun()

st.dataframe(st.session_state.df, use_container_width=True)

if not st.session_state.df.empty:
    col1, col2 = st.columns(2)
    excel_io = io.BytesIO()
    with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
        st.session_state.df.to_excel(writer, index=False)
    col1.download_button("📥 Download Master Log", excel_io.getvalue(), "requisitions.xlsx")
    
    if col2.button("📦 Generate Bulk PDFs"):
        if not os.path.exists("template.pdf"): st.error("template.pdf missing!"); st.stop()
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, 'w') as zf:
            for _, row in st.session_state.df.iterrows():
                writer = PdfWriter(); writer.append(PdfReader("template.pdf"))
                form_data = {"txt_date": datetime.now().strftime("%d-%m-%Y"), "txt_payee": row["Payee"], 
                             "txt_amount": row["Amount"], "txt_invoice": row["Invoice_No"]}
                
                mapping = {"VENTURE":"Parenthood Venture SB", "PUTRA":"Parenthood Playground SB (Putra)", "PYRAMID":"Parenthood Playground SB (Pyramid)", 
                           "TOP":"Parenthood TOP SB", "MM":"Parenthood MM SB", "MYTOWN":"Parenthood My Town SB", "SP":"Parenthood SP SB", 
                           "AMAN":"Parenthood Aman SB", "CT":"Parenthood CT SB", "IMAGO":"Parenthood YB SB (Imago)", 
                           "KUCHING":"Parenthood KBM SB (Kuching)", "BINTULU":"Parenthood KBM SB (Bintulu)", "MIRI":"Parenthood KBM SB (Miri)"}
                
                comp = row["Company"]
                if comp in mapping: form_data[mapping[comp]] = "/Yes"
                form_data[row["Release_date"]] = "/Yes"
                
                writer.update_page_form_field_values(writer.pages[0], form_data)
                writer.set_need_appearances_writer()
                pdf_io = io.BytesIO(); writer.write(pdf_io)
                zf.writestr(f"req_{row['Invoice_No']}.pdf", pdf_io.getvalue())
        col2.download_button("💾 Download All PDFs (ZIP)", zip_io.getvalue(), "requisitions.zip")

if st.button("🗑️ Reset All"):
    st.session_state.df = pd.DataFrame(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])
    st.rerun()
