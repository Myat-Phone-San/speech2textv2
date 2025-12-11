import streamlit as st
import os
import time
from typing import Tuple, Optional
import requests
from urllib.parse import urljoin 

# --- Configuration and Client Initialization (assuming secrets are set) ---
try:
    API_KEY = st.secrets["APYHUB_API_KEY"] 
except KeyError:
    st.error("🚨 API Key Error: Please set 'APYHUB_API_KEY' in your Streamlit secrets file or Streamlit Cloud Secrets.")
    st.stop()

APYHUB_BASE_URL = "https://api.apyhub.com/"
STT_ENDPOINT = urljoin(APYHUB_BASE_URL, "stt/file") 
MODEL_NAME = "ApyHub STT (multipart/form-data)" 

# --- Utility Function: Core Logic ---

def analyze_media_with_apyhub(uploaded_file, mime_type: str, language_code: str) -> Tuple[Optional[str], str]:
    
    st.info(f"Step 1/2: Preparing file **{uploaded_file.name}** for ApyHub...")
    
    # 1. Prepare data for multipart/form-data
    uploaded_file.seek(0)
    file_content = uploaded_file.read() # Read the content once
    
    # ✅ FIX APPLIED: Changed parameter name from 'file' to 'stt_file' 
    files = {
        'stt_file': (uploaded_file.name, file_content, mime_type) 
    }
    
    # The 'language' field is a simple form field.
    data = {
        'language': language_code
    }
    
    # The Authorization token is passed via a header.
    headers = {
        "apy-token": API_KEY, 
    }

    transcript_text = None
    
    try:
        # 2. Call ApyHub for Speech-to-Text
        st.info(f"Step 2/2: Calling ApyHub STT API at **{STT_ENDPOINT}** with language code: `{language_code}`...")
        start_time = time.time()
        
        response = requests.post(
            STT_ENDPOINT, 
            headers=headers, 
            data=data,
            files=files,
            timeout=300 
        )
        
        response.raise_for_status() 
        
        transcript_data = response.json()
        transcript_text = transcript_data.get("data")

        if not transcript_text:
            st.error(f"ApyHub returned success but no transcript data. Full response: {transcript_data}")
            return "Analysis failed: No transcript received.", ""
        
        end_time = time.time()
        st.success(f"Transcription completed in {end_time - start_time:.2f} seconds.")

        # --- Summarization Logic Placeholder ---
        final_result = (
            f"## 📝 Full Transcript (via ApyHub)\n"
            f"{transcript_text}\n\n"
            f"## ✅ Key Point Summary (5 Points)\n"
            f"* **NOTE:** Summarization requires a **separate** AI call (e.g., ApyHub Text Summarization) \n"
            f"* You can copy the transcript above and submit it to a text summarization tool."
        )

        return final_result, language_code
            
    except requests.exceptions.HTTPError as e: 
        st.error(f"ApyHub API Call Failed (HTTP Error): {e}. Response: {response.text}")
        st.error("Common ApyHub errors: 401 (Invalid Token), 400 (Missing 'language' parameter or invalid file).")
        return "Analysis failed due to API connection error. Check your API key and mandatory parameters.", ""
    except requests.exceptions.RequestException as e:
        st.error(f"Network/Timeout Error: {e}")
        return "Analysis failed due to network or timeout error.", ""
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return "Analysis failed due to an unexpected error.", ""


# --- Streamlit UI (Rest of the code remains the same as it was already correct) ---
st.set_page_config(page_title="Video/Audio Summarizer (ApyHub)", layout="centered")

st.markdown("""
<style>
    .stButton>button {
        background-color: #38B000; 
        color: white;
        font-size: 16px;
        padding: 10px 24px;
        border-radius: 8px;
        transition: background-color 0.3s;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        background-color: #2D8B00;
    }
    .main-header {
        color: #38B000; 
        font-weight: bold;
        text-align: center;
        padding-bottom: 10px;
        border-bottom: 2px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)


st.markdown(f'<h1 class="main-header">🎙️Video/Audio Summarizer (via ApyHub)</h1>', unsafe_allow_html=True)
st.info(f"⚡System uses the **{MODEL_NAME}**.")
st.write("Upload **any** video or audio file. You **must** select the language of the speech below, as required by the ApyHub API.")

# File Uploader
ALL_MEDIA_EXTENSIONS = [
    "mp4", "mov", "wav", "mp3", "m4a", "mkv", "avi", "flv", "wmv", 
    "ogg", "flac", "webm"
]

uploaded_file = st.file_uploader(
    "Upload Video or Audio File",
    type=ALL_MEDIA_EXTENSIONS,
    accept_multiple_files=False
)

# Language Selector (Mandatory Parameter for ApyHub STT)
language_selection = st.selectbox(
    "Select Speech Language (Mandatory)",
    options=[
        "English (en-US)", "Burmese (my-MM)", "Spanish (es-ES)", "French (fr-FR)"
    ],
    index=0,
    help="Select the BCP-47 tag corresponding to the speech in the audio/video file."
)

selected_language_code = language_selection.split("(")[-1].replace(")", "")

if uploaded_file is not None:
    # Determine MIME type 
    mime_type = uploaded_file.type 
    
    # Fallback logic for MIME type (kept for robustness)
    if not mime_type or 'octet-stream' in mime_type:
        ext = os.path.splitext(uploaded_file.name)[1].lower().replace('.', '')
        if ext == 'mp3': mime_type = 'audio/mpeg'
        elif ext == 'wav': mime_type = 'audio/wav'
        elif ext == 'mp4': mime_type = 'video/mp4'
        elif ext == 'mov': mime_type = 'video/quicktime'
        elif ext == 'm4a': mime_type = 'audio/m4a'
        elif ext == 'ogg': mime_type = 'audio/ogg'
        else: mime_type = 'application/octet-stream' 
        
    st.success(f"File uploaded: **{uploaded_file.name}** (Detected MIME: `{mime_type}`) - Ready to process.")
    
    if st.button("Generate Transcript and Summary"):
        
        if uploaded_file.size > (200 * 1024 * 1024): 
            st.error("File size limit exceeded. Please upload a file smaller than 200MB.")
        else:
            # Main processing function call
            with st.spinner(f"Processing with ApyHub..."):
                analysis_result, _ = analyze_media_with_apyhub(uploaded_file, mime_type, selected_language_code)
            
            # Display the result
            if analysis_result and not analysis_result.startswith("Analysis failed"):
                st.markdown(analysis_result)
                st.success(f"Process complete: Transcription extracted by ApyHub.")
            else:
                st.error("The analysis failed. Please check the error messages above for details.")
