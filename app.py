import streamlit as st
import pandas as pd
import json, io, zipfile
from datetime import datetime
from groq import Groq
from pypdf import PdfReader, PdfWriter

st.set_page_config(page_title="Enterprise Requisition", layout="wide")
st.title("🏢 Enterprise Requisition System")

# Configuration in sidebar
api_key = st.sidebar.text_input("Groq API Key:", type="password")
uploaded_template = st.sidebar.file_uploader("Upload PDF Template", type="pdf")

# State Management
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])

# Input Section
st.subheader("Data Input")
raw_text = st.text_area("Paste invoice data:", height=150)

# Process Button (Standard)
if st.button("Process Data"):
    if not api_key:
        st.error("Please enter your Groq API Key in the sidebar.")
    elif not raw_text:
        st.warning("Please paste some data to process.")
    else:
        try:
            client = Groq(api_key=api_key)
            with st.spinner("Processing..."):
                res = client.chat.completions.create(
                    messages=[{"role": "system", "content": "Extract data to JSON. Keys: Company, Payee, Amount, Invoice_No, Release_date."}, 
                              {"role": "user", "content": raw_text}],
                    model="llama-3.3-70b-versatile", response_format={"type": "json_object"}
                )
                data = json.loads(res.choices[0].message.content)
                
                # Update DataFrame
                new_data = data.get("items", [])
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame(new_data)], ignore_index=True)
                st.success("Data added!")
        except Exception as e:
            st.error(f"Error: {e}")

# Display
st.subheader("Current Data")
st.dataframe(st.session_state.df)

# Download Section
if not st.session_state.df.empty:
    if st.button("Generate PDFs"):
        if not uploaded_template:
            st.error("Please upload a template PDF.")
        else:
            # Simple PDF logic
            st.write("PDF generation triggered...")
            # (Insert your specific PDF zip logic here)
