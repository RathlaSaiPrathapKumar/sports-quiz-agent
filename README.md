# AI-Powered Sports Quiz Generator (Statupbox)

This project is an interactive, factually grounded web application that generates and hosts sports trivia quizzes. It implements Retrieval-Augmented Generation (RAG) to solve the problem of LLM hallucinations.

---

## How It Works (RAG Architecture)

Rather than letting the Large Language Model make up quiz answers and explanations, the application functions like an "open-book exam":

```
[User Input: Sport & Difficulty]
       │
       ▼
 ┌───────────┐     1. Query local vectors       ──> [ChromaDB Vector Store]
 │ AI Agent  │ ──> 2. Query live internet news  ──> [DuckDuckGo Search]
 └───────────┘
       │
       ▼  (Gathers ground truth snippets)
 ┌────────────────────────────────────────────────────────┐
 │ Prompt Compilation: System Rules + Retrieved Context  │
 └────────────────────────────────────────────────────────┘
       │
       ▼  (Requests Structured JSON schema)
 ┌─────────────────────────────────┐
 │ LLM (Google Gemini / OpenAI)    │
 └─────────────────────────────────┘
       │
       ▼  (Strict JSON output parsed)
 [Interactive 3-Question Game rendered in Streamlit UI]
```

1. **Local Vector Database (ChromaDB)**: Stores historic facts (loaded from `data/sports_facts.json`). We query ChromaDB for matching documents using cosine similarities.
2. **Live Web Search (DuckDuckGo)**: Performs an on-the-fly anonymous search query (e.g. *"Tennis latest tournament results 2026"*) to fetch current news and live score details.
3. **Orchestrator Prompt Blending**: Merges both retrieved blocks into a unified system prompt and passes it to the LLM (either Google Gemini or OpenAI).
4. **Structured JSON Output**: Commands the LLM to format response data *strictly* in JSON mode, ensuring program parsing never breaks.
5. **Interactive UI**: Hosts a playable game with instant feedback, explanation alerts, scores, and a copy-pasteable social share text block.

---

## Project Structure

```
sports-quiz-agent/
│
├── .env                  # Contains API keys (excluded from Git)
├── requirements.txt      # List of dependencies to install
├── README.md             # This guide
├── app.py                # Main Streamlit dashboard (Playable UI, Admin Panel)
│
├── data/
│   └── sports_facts.json # Local historic database (raw facts in JSON format)
│
├── chroma_db/            # Persistent vector database files (ChromaDB)
│
└── src/
    ├── __init__.py       # Package initializer
    ├── config.py         # Loads environment keys & path settings
    ├── database.py       # Interacts with ChromaDB (Insert, Query, Read)
    ├── search.py         # Interacts with DuckDuckGo Search API
    └── generator.py      # Blends context & calls OpenAI/Gemini/Mock APIs
```

---

## Setup & Running the Application

### 1. Configure API Keys
Open the `.env` file in the project folder and paste either your Google Gemini or OpenAI API keys:
```env
GEMINI_API_KEY=your_gemini_key_here
OPENAI_API_KEY=your_openai_key_here
```
*Note: If no API keys are provided, the application will automatically enter **Offline Mock Mode**, allowing you to test and play pre-compiled quizzes immediately!*

### 2. Run the App
With your virtual environment active, run the Streamlit server:
```bash
streamlit run app.py
```

---

## Features
- **🎮 Play Interactive Quiz**: Answer generated questions. Buttons change colors and reveal explanations dynamically.
- **📱 Social Media Share Text**: Obtain copy-pasteable quiz blocks ready to post.
- **📚 Vector Knowledge Base**: Administrative panel allowing you to view items in ChromaDB or insert new facts into vector embeddings on-the-fly.
- **🔍 RAG Pipeline Auditor**: Inspect the raw queries, live search snippets, and context injected directly into the system prompt.
