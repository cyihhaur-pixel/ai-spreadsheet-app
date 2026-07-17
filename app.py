import streamlit as st
import pandas as pd
import json
import os
from groq import Groq

# Page configuration
st.set_page_config(page_title="AI Spreadsheet Filler", page_icon="📊", layout="wide")

st.title("📊 AI-Powered Spreadsheet Assistant (Groq)")
st.write("Paste your raw invoice text, receipt data, or email below. The AI will extract the data and fill your spreadsheet columns automatically.")

# Sidebar for configuration
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Enter Groq API Key:", type="password", value=os.environ.get("GROQ_API_KEY", ""))
model_choice = st.sidebar.selectbox(
    "Select AI Model:",
    ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
)

# Initialize Session State for the spreadsheet data if it doesn't exist
if "spreadsheet_df" not in st.session_state:
    st.session_state.spreadsheet_df = pd.DataFrame(columns=[
        "Company", "Payee", "Amount", "Invoice_No", "Release_date"
    ])

# Main Layout: Split screen for Input and Live Table
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📥 Input Raw Data")
    raw_text = st.text_area("Paste text here (e.g., email context, invoice breakdown):", height=300, placeholder="Example:\nWe received invoice #INV-9922 from Acme Corp for a payment of $1,250.50 to John Doe. Please release funds by October 24th, 2026.")
    
    analyze_btn = st.button("⚡ Analyze & Populate", type="primary")

with col2:
    st.subheader("📋 Your Live Spreadsheet")
    
    # Reset table button
    if st.button("🗑️ Clear Table"):
        st.session_state.spreadsheet_df = pd.DataFrame(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])
        st.rerun()

    # Display the current dataframe
    st.dataframe(st.session_state.spreadsheet_df, use_container_width=True)

    # Download options
    if not st.session_state.spreadsheet_df.empty:
        st.write("---")
        st.subheader("💾 Export Data")
        
        # Convert to Excel
        @st.cache_data
        def convert_df_to_excel(df):
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            return output.getvalue()
        
        excel_data = convert_df_to_excel(st.session_state.spreadsheet_df)
        
        st.download_button(
            label="📥 Download as Excel (.xlsx)",
            data=excel_data,
            file_name="requisitions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Processing the AI logic
if analyze_btn:
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar to proceed.")
    elif not raw_text.strip():
        st.warning("Please paste some text data to parse.")
    else:
        with st.spinner("Groq AI is analyzing and structuring the data..."):
            try:
                # Initialize Groq Client
                client = Groq(api_key=api_key)
                
                # System prompt forcing structured JSON output mapping your image columns
                system_prompt = (
                    "You are an expert data parsing assistant. Your task is to extract information from the user's text "
                    "and format it into a strictly structured JSON object matching these specific keys:\n"
                    "- Company\n"
                    "- Payee\n"
                    "- Amount\n"
                    "- Invoice_No\n"
                    "- Release_date\n\n"
                    "Rules:\n"
                    "1. If a field is not found in the text, return null for that field.\n"
                    "2. Return ONLY a single valid JSON object. Do not include markdown code blocks, backticks, or extra conversational text."
                )
                
                # Call Groq API using JSON mode
                completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": raw_text}
                    ],
                    model=model_choice,
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                
                # Parse the response text
                extracted_data = json.loads(completion.choices[0].message.content)
                
                # Create a temporary DataFrame for the new row
                new_row = pd.DataFrame([extracted_data])
                
                # Reorder columns just to make sure it matches your spreadsheet perfectly
                new_row = new_row.reindex(columns=["Company", "Payee", "Amount", "Invoice_No", "Release_date"])
                
                # Append to existing session data
                st.session_state.spreadsheet_df = pd.concat([st.session_state.spreadsheet_df, new_row], ignore_index=True)
                
                st.success("Data successfully extracted and added to the spreadsheet view!")
                st.rerun()

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
