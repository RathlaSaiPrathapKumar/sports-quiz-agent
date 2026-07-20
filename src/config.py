import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Centralized configurations
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check Streamlit secrets when deployed to Streamlit Community Cloud
try:
    import streamlit as st
    if not OPENAI_API_KEY and hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
        OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    if not GEMINI_API_KEY and hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

# Check keys
if not OPENAI_API_KEY and not GEMINI_API_KEY:
    print("[WARNING]: Both OPENAI_API_KEY and GEMINI_API_KEY are missing. Please configure one in your .env file or Streamlit Secrets!")
elif OPENAI_API_KEY:
    print("[INFO]: OpenAI API key is configured.")
elif GEMINI_API_KEY:
    print("[INFO]: Gemini API key is configured.")

# Database configurations
DB_PERSIST_PATH = "./chroma_db"
FACTS_JSON_PATH = "./data/sports_facts.json"

