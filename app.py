import streamlit as st
import pandas as pd
import json
from groq import Groq

# Page Setup
st.set_page_config(page_title="Enterprise Requisition", layout="wide")
st.title("🏢 Enterprise Requisition System")

# Initialize Session State
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])

# Sidebar
api_key = st.sidebar.text_input("Groq API Key:", type="password")

# Input Section
st.subheader("Bulk Input")
raw_text = st.text_area("Paste invoice data:", height=150)

if st.button("Process Data"):
    if not api_key:
        st.error("Please enter your Groq API Key in the sidebar.")
    elif not raw_text.strip():
        st.warning("Please paste some data to process.")
    else:
        try:
            client = Groq(api_key=api_key)
            with st.spinner("Processing with AI..."):
                # System prompt refined for strict structure
                prompt = (
                    "Extract invoice data into a JSON object. "
                    "The JSON must have a single key 'items', which is a list of objects. "
                    "Each object must have these keys: Company, Payee, Amount, Invoice_No, Release_date. "
                    "Return ONLY valid JSON."
                )
                
                res = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": raw_text}
                    ],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"}
                )
                
                # Parse output
                content = json.loads(res.choices[0].message.content)
                
                # Debugging output - this will show you what the AI returned
                st.write("--- Debug View ---")
                st.json(content)
                
                # Data extraction
                extracted_items = content.get("items", [])
                
                if extracted_items:
                    new_data = pd.DataFrame(extracted_items)
                    st.session_state.df = pd.concat([st.session_state.df, new_data], ignore_index=True)
                    st.success(f"Successfully added {len(extracted_items)} items!")
                else:
                    st.error("The AI did not return any items under the key 'items'. Check the debug view above.")
                    
        except Exception as e:
            st.error(f"Error: {e}")

# Display Table
st.subheader("Current Data")
if not st.session_state.df.empty:
    st.data_editor(st.session_state.df, use_container_width=True)
else:
    st.info("No data in table yet.")
