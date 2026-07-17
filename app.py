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

raw_text = st.text_area("Paste ALL your invoice details here:", height=200)

if st.button("⚡ Process & Add to Batch"):
    if not api_key: st.error("Need API Key"); st.stop()
    client = Groq(api_key=api_key)
    
    # AI will now return a list of objects
    system_prompt = (
        "Extract all payment items from the text. Return a JSON object with a key 'items' "
        "containing a list of objects, each with: Company, Payee, Amount, Invoice_No, Release_date.\n"
        "1. Company: Use ONLY: venture, putra, pyramid, top, mm, mytown, sp, aman, ct, imago, kuching, bintulu, miri.\n"
        "2. Amount: Format as '5,000.00'.\n"
        "3. If info is missing, use 'N/A'."
    )
    
    res = client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
        model="llama-3.3-70b-versatile", response_format={"type": "json_object"}
    )
    
    response_data = json.loads(res.choices[0].message.content)
    
    # Process the list of items
    for item in response_data.get("items", []):
        # Bulletproof: Use .get() and safe capitalization
        comp = str(item.get("Company", "N/A")).upper()
        
        new_row = {
            "Company": comp,
            "Payee": str(item.get("Payee", "N/A")).upper(),
            "Amount": str(item.get("Amount", "0.00")),
            "Invoice_No": str(item.get("Invoice_No", "N/A")),
            "Release_date": str(item.get("Release_date", "Urgent"))
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
    st.rerun()

# Display
st.dataframe(st.session_state.df, use_container_width=True)
# ... (rest of your download/export logic remains the same)
