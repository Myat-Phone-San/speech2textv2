import streamlit as st
import os
import tempfile
import time
from typing import Tuple, Optional
import requests
import json
import base64
from urllib.parse import urljoin # Utility for constructing API URLs

# --- Configuration and Client Initialization ---
# ❗ IMPORTANT: Ensure APYHUB_API_KEY is set in Streamlit secrets
try:
    # Attempt to retrieve API Key from Streamlit secrets
    API_KEY = st.secrets["APYHUB_API_KEY"] 
except KeyError:
    st.error("🚨 API Key Error: Please set 'APYHUB_API_KEY' in your Streamlit secrets file or Streamlit Cloud Secrets.")
    st.stop()

# --- ApyHub API Configuration ---
# Base URL for ApyHub APIs (This is an assumed endpoint, check ApyHub's official documentation)
APYHUB_BASE_URL = "https://api.apyhub.com/"
# Endpoint for Speech-to-Text conversion (Assumed endpoint)
STT_ENDPOINT = urljoin(APYHUB_BASE_URL, "ai/convert/speech-to-text")
# Model/Provider to use (ApyHub might allow specifying an underlying provider)
MODEL_NAME = "apyhub-stt-standard" 

# --- Utility Function: Core Logic ---

def analyze_media_with_apyhub(uploaded_file, mime_type: str) -> Tuple[Optional[str], str]:
    """
    1. Reads the audio/video file's content and converts it to Base64 (A common API pattern).
    2. Sends the Base64 data to the ApyHub Speech-to-Text API.
    3. Sends the resulting transcript (or the file directly) to a Generative Model (Hypothetical ApyHub Text Generator)
       for summarization, OR structures the final output based on the transcript result.
       
    Returns: (analysis_result_text, detected_language_code)
    """
    
    st.info(f"Step 1/2: Preparing file **{uploaded_file.name}** for ApyHub...")
    
    # 1. Read file and convert to Base64
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    base64_content = base64.b64encode(file_bytes).decode('utf-8')
    
    # Check if the file is too large for a Base64-in-body approach (API limits may vary)
    if len(base64_content) > (20 * 1024 * 1024): # Example: limiting to 20MB of Base64 content (approx 15MB file)
        st.warning("Warning: File is large. ApyHub API may require a different upload method (e.g., pre-signed URL) for files this size.")
        
    
    # ApyHub STT Request Payload
    payload = {
        "input": {
            "type": "file",
            "file": base64_content,
            "filename": uploaded_file.name,
            "mimetype": mime_type
        },
        # Assuming ApyHub allows specifying output format or language hints
        "output": {
            "type": "text"
        }
    }
    
    headers = {
        "Authorization": f"Token {API_KEY}",
        "Content-Type": "application/json"
    }

    transcript_text = None
    
    try:
        # 2. Call ApyHub for Speech-to-Text
        st.info(f"Step 2a/2: Calling ApyHub STT API at {STT_ENDPOINT}...")
        start_time = time.time()
        
        response = requests.post(
            STT_ENDPOINT, 
            headers=headers, 
            data=json.dumps(payload), 
            timeout=300 # 5 minutes timeout for long transcriptions
        )
        
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        
        # Assume successful response returns a JSON with the transcript
        transcript_data = response.json()
        transcript_text = transcript_data.get("data", {}).get("text", transcript_data.get("data"))

        if not transcript_text:
            st.error(f"ApyHub returned success but no transcript data. Full response: {transcript_data}")
            return "Analysis failed: No transcript received.", ""
        
        st.success(f"Transcription completed in {time.time() - start_time:.2f} seconds.")

        # --- Summarization Logic (Option A: If ApyHub has a separate summarization endpoint) ---
        # For simplicity and to match the original Gemini logic, we'll implement Option B
        
        # --- Summarization Logic (Option B: Simple Structure) ---
        # This part simulates the summarization without a second API call,
        # since ApyHub's public docs don't show a combined STT+Summary endpoint.
        # A real application would require a second 'Text Summarization' API call.
        
        final_result = (
            f"## 📝 Full Transcript (via ApyHub)\n"
            f"{transcript_text}\n\n"
            f"## ✅ Key Point Summary (5 Points)\n"
            f"* **NOTE:** The summarization part requires a separate ApyHub AI call "
            f"(e.g., using a Text Summarization API) which is not implemented here. \n"
            f"* Please copy the transcript above and submit it to a text summarization tool."
        )

        return final_result, "Unknown"
            
    except requests.exceptions.HTTPError as e: 
        st.error(f"ApyHub API Call Failed (HTTP Error): {e}. Response: {response.text}")
        return "Analysis failed due to API connection error.", ""
    except requests.exceptions.RequestException as e:
        st.error(f"Network/Timeout Error: {e}")
        return "Analysis failed due to network or timeout error.", ""
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return "Analysis failed due to an unexpected error.", ""
    finally:
        # No remote file cleanup needed as Base64 is sent in the request body.
        pass


# --- Streamlit UI ---
st.set_page_config(page_title="Video/Audio Summarizer (ApyHub)", layout="centered")

st.markdown("""
<style>
    /* Custom Styling for aesthetics */
    .stButton>button {
        background-color: #38B000; /* ApyHub-like color */
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
        color: #38B000; /* ApyHub-like color */
        font-weight: bold;
        text-align: center;
        padding-bottom: 10px;
        border-bottom: 2px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)


st.markdown(f'<h1 class="main-header">🎙️Video/Audio Summarizer (via ApyHub)</h1>', unsafe_allow_html=True)
st.info(f"⚡System uses the **ApyHub Convert Speech-to-Text API**.")
st.write("Upload **any** video or audio file (e.g., MP3, MP4, WAV). Note: APIs using Base64 in the request body often have size limitations.")

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

if uploaded_file is not None:
    # Determine MIME type 
    mime_type = uploaded_file.type 
    
    # Fallback logic for MIME type (kept from original code)
    if not mime_type or 'octet-stream' in mime_type:
        ext = os.path.splitext(uploaded_file.name)[1].lower().replace('.', '')
        if ext == 'mp3': mime_type = 'audio/mpeg'
        elif ext == 'wav': mime_type = 'audio/wav'
        elif ext == 'mp4': mime_type = 'video/mp4'
        elif ext == 'mov': mime_type = 'video/quicktime'
        elif ext == 'm4a': mime_type = 'audio/m4a'
        elif ext == 'ogg': mime_type = 'audio/ogg'
        else: mime_type = 'application/octet-stream' # Default fallback
        
    st.success(f"File uploaded: **{uploaded_file.name}** (Detected MIME: `{mime_type}`) - Ready to process.")
    
    if st.button("Generate Transcript and Summary"):
        
        # Check size limit (Note: Base64 size limit is different from file size limit)
        # Using a conservative file size limit for Base64 embedding
        if uploaded_file.size > (15 * 1024 * 1024): 
            st.error("File size limit exceeded for Base64 API call. Please upload a file smaller than 15MB.")
        else:
            # Main processing function call
            with st.spinner(f"Processing with ApyHub..."):
                analysis_result, _ = analyze_media_with_apyhub(uploaded_file, mime_type)
            
            # Display the result
            if analysis_result and not analysis_result.startswith("Analysis failed"):
                st.markdown(analysis_result)
                st.success(f"Process complete: Transcription extracted by **{MODEL_NAME}**.")
            else:
                st.error("The analysis failed. Please check the error messages above for details.")