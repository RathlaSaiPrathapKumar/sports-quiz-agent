import streamlit as st
import os
import json
import time
import datetime

# Setup page configurations
st.set_page_config(page_title="Statupbox Sports Quiz Agent", page_icon="🏆", layout="wide")

# Custom CSS for modern glassmorphism design and micro-animations
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Outfit', sans-serif;
}

/* Main Background */
[data-testid="stAppViewContainer"] {
    background-color: #0F172A;
}

/* Sidebar Custom Styling */
[data-testid="stSidebar"] {
    background-color: #1E293B !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Title Gradient Header */
.gradient-title {
    background: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 2.8rem;
    margin-bottom: 0.2rem;
}

.gradient-subtitle {
    color: #94A3B8;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}

/* Glassmorphic Quiz Card */
.quiz-card {
    background: rgba(30, 41, 59, 0.6);
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 28px;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.25);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
}

/* Response Banners */
.result-banner-correct {
    background: rgba(16, 185, 129, 0.15);
    border-radius: 12px;
    border: 1px solid rgba(16, 185, 129, 0.4);
    padding: 20px;
    margin-top: 15px;
    color: #34D399;
}

.result-banner-incorrect {
    background: rgba(239, 68, 68, 0.15);
    border-radius: 12px;
    border: 1px solid rgba(239, 68, 68, 0.4);
    padding: 20px;
    margin-top: 15px;
    color: #F87171;
}

/* Custom Interactive Button Hover Effects */
div.stButton > button {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px;
    font-weight: 600;
    padding: 0.6rem 1.5rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

div.stButton > button:hover {
    background-color: #10B981;
    color: #FFFFFF;
    border-color: #10B981;
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.45);
    transform: translateY(-2px);
}

div.stButton > button:active {
    transform: translateY(1px);
}
</style>
""", unsafe_allow_html=True)

# Imports from our modules
try:
    from src.generator import compile_quiz_data
    from src.database import setup_and_populate_db, get_all_facts, add_custom_fact
except ImportError:
    st.error("Error importing local modules. Make sure you are running Streamlit inside the project directory and package modules are installed.")

# Initialize the vector DB with offline facts on startup
@st.cache_resource
def prepare_knowledge_base():
    try:
        setup_and_populate_db()
        return True
    except Exception as e:
        st.sidebar.error(f"Failed to populate database: {e}")
        return False

db_ready = prepare_knowledge_base()

# Initialize session states to remember selections and generation results across page reruns
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "quiz_context" not in st.session_state:
    st.session_state.quiz_context = None
if "quiz_source" not in st.session_state:
    st.session_state.quiz_source = None
if "sport_choice" not in st.session_state:
    st.session_state.sport_choice = None
if "difficulty_choice" not in st.session_state:
    st.session_state.difficulty_choice = None
if "score" not in st.session_state:
    st.session_state.score = 0
if "answers_submitted" not in st.session_state:
    # Tracks {q_index: option_selected}
    st.session_state.answers_submitted = {}
if "revealed_answers" not in st.session_state:
    # Tracks {q_index: is_revealed}
    st.session_state.revealed_answers = {}
if "quiz_history" not in st.session_state:
    # Stores list of completed quiz dictionaries
    st.session_state.quiz_history = []
if "current_quiz_id" not in st.session_state:
    st.session_state.current_quiz_id = None
if "history_saved" not in st.session_state:
    st.session_state.history_saved = False

# Sidebar inputs
st.sidebar.markdown("<h2 style='color:#10B981;'>🏆 Quiz Settings</h2>", unsafe_allow_html=True)

sport_choice = st.sidebar.selectbox(
    "Select Sport Category", 
    ["Cricket", "Football", "Badminton", "Basketball", "Tennis"]
)
difficulty = st.sidebar.select_slider(
    "Select Difficulty Level", 
    options=["Easy", "Medium", "Hard"]
)


provider_choice = st.sidebar.selectbox(
    "Preferred LLM Model",
    ["Auto-Detect", "Google Gemini", "OpenAI", "Offline Mock Mode"]
)

# Button to trigger quiz compilation pipeline
st.sidebar.markdown("---")
if st.sidebar.button("🎮 Generate Fresh Quiz", use_container_width=True):
    # Map selection to internal provider strings
    provider_map = {
        "Auto-Detect": None,
        "Google Gemini": "Gemini",
        "OpenAI": "OpenAI",
        "Offline Mock Mode": "Mock"
    }
    
    # Show loading spinner during DB query + DDG Search + LLM invocation
    with st.spinner("🔍 Fetching history from database & search engine updates..."):
        try:
            quiz, context, source = compile_quiz_data(
                sport=sport_choice, 
                difficulty=difficulty, 
                num_questions=6,
                provider=provider_map[provider_choice]
            )
            
            # Reset game states
            st.session_state.quiz_data = quiz
            st.session_state.quiz_context = context
            st.session_state.quiz_source = source
            st.session_state.sport_choice = sport_choice
            st.session_state.difficulty_choice = difficulty
            st.session_state.score = 0
            st.session_state.answers_submitted = {}
            st.session_state.revealed_answers = {}
            st.session_state.current_quiz_id = f"quiz_{int(time.time())}"
            st.session_state.history_saved = False
            
            st.sidebar.success(f"Generated successfully via {source}!")
        except Exception as e:
            st.sidebar.error(f"Generation error: {e}")

# Header display
st.markdown("<h1 class='gradient-title'>Statupbox AI Sports Quiz Agent</h1>", unsafe_allow_html=True)
st.markdown("<p class='gradient-subtitle'>Factually-grounded RAG quiz games blending local Vector DB (ChromaDB) with live search (DuckDuckGo)</p>", unsafe_allow_html=True)

# Application tabs
tab_play, tab_history, tab_socials, tab_database, tab_diagnostics = st.tabs([
    "🎮 Play Interactive Quiz", 
    "📜 Quiz History & Downloads",
    "📱 Social Media Share Text", 
    "📚 Vector Knowledge Base", 
    "🔍 RAG Pipeline Auditor"
])

# -----------------
# TAB 1: PLAY QUIZ
# -----------------
with tab_play:
    if st.session_state.quiz_data and "quiz" in st.session_state.quiz_data:
        quiz_list = st.session_state.quiz_data["quiz"]
        sport = st.session_state.sport_choice
        diff = st.session_state.difficulty_choice
        
        st.markdown(f"### Current Quiz: **{sport}** ({diff} - 6 Questions)")
        st.markdown(f"Generated via: `{st.session_state.quiz_source}`")
        st.write("Complete the multiple-choice questions below:")
        st.write("---")
        
        # Display each question inside a card
        for idx, q_item in enumerate(quiz_list):
            st.markdown(f"""
            <div class='quiz-card'>
                <h4 style='color:#38BDF8; margin-top:0;'>Question {idx+1}: {q_item['question']}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Options radio input
            options_dict = q_item["options"]
            # Format label choices as "A) Option text"
            formatted_choices = [f"{k}) {v}" for k, v in options_dict.items()]
            
            # Retrieve previous answers if page reruns
            default_selection_idx = None
            if idx in st.session_state.answers_submitted:
                selected_letter = st.session_state.answers_submitted[idx]
                default_selection_idx = list(options_dict.keys()).index(selected_letter)
                
            selected_option = st.radio(
                f"Choose option for Question {idx+1}:",
                options=formatted_choices,
                index=default_selection_idx,
                key=f"q_radio_{idx}",
                label_visibility="collapsed"
            )
            
            # Extract selected letter (first character)
            selected_letter = selected_option[0] if selected_option else None
            
            col1, col2 = st.columns([1, 4])
            with col1:
                # Submit Answer Button
                is_revealed = st.session_state.revealed_answers.get(idx, False)
                if st.button("Submit Answer", key=f"submit_btn_{idx}", disabled=is_revealed):
                    st.session_state.answers_submitted[idx] = selected_letter
                    st.session_state.revealed_answers[idx] = True
                    
                    # Update score if correct
                    if selected_letter == q_item["correct_answer"]:
                        st.session_state.score += 1
                    st.rerun()
            
            # Display results if user submitted answer
            if st.session_state.revealed_answers.get(idx, False):
                user_ans = st.session_state.answers_submitted.get(idx)
                correct_ans = q_item["correct_answer"]
                correct_text = f"{correct_ans}) {options_dict[correct_ans]}"
                
                if user_ans == correct_ans:
                    st.markdown(f"""
                    <div class='result-banner-correct'>
                        <strong>✅ Correct!</strong><br>
                        <strong>Answer:</strong> {correct_text}<br>
                        <strong>Fact Grounding:</strong> {q_item['explanation']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    user_text = f"{user_ans}) {options_dict[user_ans]}" if user_ans else "None"
                    st.markdown(f"""
                    <div class='result-banner-incorrect'>
                        <strong>❌ Incorrect!</strong><br>
                        <strong>Your Answer:</strong> {user_text}<br>
                        <strong>Correct Answer:</strong> {correct_text}<br>
                        <strong>Fact Grounding:</strong> {q_item['explanation']}
                    </div>
                    """, unsafe_allow_html=True)
            st.write("")
            st.write("---")
            
        # Display Final Score Card at bottom
        total_questions = len(quiz_list)
        submitted_count = len(st.session_state.revealed_answers)
        
        if submitted_count == total_questions:
            score = st.session_state.score
            pct = int((score / total_questions) * 100)
            
            st.markdown(f"""
            <div class='quiz-card' style='text-align: center; border-color: #10B981;'>
                <h3 style='color:#10B981; margin:0;'>🎉 Quiz Completed!</h3>
                <h1 style='font-size: 4rem; color: #FFF; margin: 10px 0;'>{score} / {total_questions}</h1>
                <p style='color:#94A3B8; font-size:1.2rem;'>You scored <strong>{pct}%</strong></p>
            </div>
            """, unsafe_allow_html=True)
            
            if score == total_questions:
                st.balloons()
            
            # Create download file content
            download_content = f"🏆 Statupbox Sports Quiz Attempt Report 🏆\n"
            download_content += f"=========================================\n"
            download_content += f"Sport: {sport}\n"
            download_content += f"Difficulty: {diff}\n"
            download_content += f"Final Score: {score} / {total_questions} ({pct}%)\n"
            download_content += f"=========================================\n\n"
            
            for q_idx, q_item in enumerate(quiz_list):
                user_ans = st.session_state.answers_submitted.get(q_idx)
                correct_ans = q_item["correct_answer"]
                is_correct_str = "CORRECT ✅" if user_ans == correct_ans else "INCORRECT ❌"
                
                download_content += f"Question {q_idx+1}: {q_item['question']}\n"
                for opt, opt_val in q_item["options"].items():
                    download_content += f"  {opt}) {opt_val}\n"
                download_content += f"Your Answer: {user_ans}) {q_item['options'].get(user_ans, 'None')} ({is_correct_str})\n"
                download_content += f"Correct Answer: {correct_ans}) {q_item['options'][correct_ans]}\n"
                download_content += f"Explanation: {q_item['explanation']}\n"
                download_content += f"-----------------------------------------\n\n"
            
            # Save to quiz history if not saved yet
            if not st.session_state.history_saved:
                timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                history_entry = {
                    "id": st.session_state.current_quiz_id or f"quiz_{int(time.time())}",
                    "timestamp": timestamp_str,
                    "sport": sport,
                    "difficulty": diff,
                    "score": score,
                    "total": total_questions,
                    "pct": pct,
                    "quiz_list": quiz_list,
                    "answers_submitted": dict(st.session_state.answers_submitted),
                    "download_content": download_content
                }
                st.session_state.quiz_history.insert(0, history_entry)
                st.session_state.history_saved = True
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                st.download_button(
                    label="📥 Download Quiz Report",
                    data=download_content,
                    file_name=f"sports_quiz_{sport.lower()}_{diff.lower()}_score_{score}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with btn_col2:
                if st.button("🔄 Restart Current Quiz", use_container_width=True):
                    st.session_state.score = 0
                    st.session_state.answers_submitted = {}
                    st.session_state.revealed_answers = {}
                    st.session_state.history_saved = False
                    st.rerun()
    else:
        st.info("👈 Please select a Sport and Difficulty from the sidebar, then click 'Generate Fresh Quiz' to begin!")

# -----------------
# TAB 2: QUIZ HISTORY & DOWNLOADS
# -----------------
with tab_history:
    st.subheader("📜 Quiz History & Completed Attempts")
    st.write("Review past completed quizzes, check your scores, and download full text reports for any previous attempt.")
    
    if st.session_state.quiz_history:
        # History Statistics Overview
        total_attempts = len(st.session_state.quiz_history)
        avg_score_pct = int(sum(h["pct"] for h in st.session_state.quiz_history) / total_attempts)
        best_score_pct = max(h["pct"] for h in st.session_state.quiz_history)
        
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.metric("Total Quizzes Attempted", f"{total_attempts}")
        with stat_col2:
            st.metric("Average Score", f"{avg_score_pct}%")
        with stat_col3:
            st.metric("Best Score", f"{best_score_pct}%")
            
        st.write("---")
        
        # Display list of historical records
        for record in st.session_state.quiz_history:
            badge_color = "#10B981" if record["pct"] >= 70 else ("#F59E0B" if record["pct"] >= 50 else "#EF4444")
            
            st.markdown(f"""
            <div class='quiz-card' style='border-left: 5px solid {badge_color}; margin-bottom: 16px; padding: 20px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <h4 style='color: #F8FAFC; margin: 0;'>{record['sport']} ({record['difficulty']})</h4>
                        <small style='color: #94A3B8;'>Attempted on: {record['timestamp']}</small>
                    </div>
                    <div style='text-align: right;'>
                        <span style='font-size: 1.6rem; font-weight: bold; color: {badge_color};'>{record['score']} / {record['total']}</span>
                        <span style='color: #94A3B8;'> ({record['pct']}%)</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            h_col1, h_col2 = st.columns([3, 1])
            with h_col1:
                with st.expander(f"🔍 Inspect Questions Breakdown ({record['sport']})"):
                    for q_i, q_data in enumerate(record["quiz_list"]):
                        u_ans = record["answers_submitted"].get(q_i)
                        c_ans = q_data["correct_answer"]
                        status_tag = "✅ Correct" if u_ans == c_ans else "❌ Incorrect"
                        st.markdown(f"**Q{q_i+1}: {q_data['question']}** ({status_tag})")
                        st.markdown(f"- Your Answer: `{u_ans}) {q_data['options'].get(u_ans, 'None')}`")
                        st.markdown(f"- Correct Answer: `{c_ans}) {q_data['options'][c_ans]}`")
                        st.markdown(f"- Grounding: *{q_data['explanation']}*")
                        st.write("")
            with h_col2:
                st.download_button(
                    label="📥 Download Report",
                    data=record["download_content"],
                    file_name=f"history_{record['sport'].lower()}_{record['id']}.txt",
                    mime="text/plain",
                    key=f"dl_btn_{record['id']}",
                    use_container_width=True
                )
            st.write("---")
    else:
        st.info("No completed quizzes yet. Complete a quiz to view your history and download past reports here!")

# -----------------
# TAB 2: SOCIALS
# -----------------
with tab_socials:
    if st.session_state.quiz_data and "quiz" in st.session_state.quiz_data:
        quiz_list = st.session_state.quiz_data["quiz"]
        sport = st.session_state.sport_choice
        diff = st.session_state.difficulty_choice
        
        # Compile plain text representation
        social_text = f"🏆 AI-POWERED SPORTS QUIZ: {sport.upper()} ({diff.upper()}) 🏆\n"
        social_text += "Grounded facts via ChromaDB + DuckDuckGo Web Search\n\n"
        
        for idx, q_item in enumerate(quiz_list):
            social_text += f"Question {idx+1}: {q_item['question']}\n"
            for opt, opt_val in q_item["options"].items():
                social_text += f"  {opt}) {opt_val}\n"
            social_text += f"Correct Answer: {q_item['correct_answer']}\n"
            social_text += f"Explanation: {q_item['explanation']}\n"
            social_text += "----------------------------------------\n\n"
            
        social_text += "Generated by Statupbox Sports Quiz Agent 🚀"
        
        st.subheader("Copy to Socials")
        st.write("Copy and paste this structured output directly to your social platforms:")
        st.text_area("Plain Text Quiz (Formatted)", value=social_text, height=350)
    else:
        st.info("No quiz generated yet. Generate a quiz from the sidebar first.")

# -----------------
# TAB 3: DATABASE
# -----------------
with tab_database:
    st.subheader("📚 ChromaDB Vector Database Manager")
    st.write("ChromaDB vectorizes local text using cosine similarities. Below you can view facts currently stored or feed in new ones.")
    
    if db_ready:
        # Load facts
        facts = get_all_facts()
        st.write(f"**Total Records Vectorized:** `{len(facts)}` facts.")
        
        # Add new custom fact form
        with st.expander("➕ Vectorize New Custom Fact (RAG Injection)"):
            st.write("Submit a fact to instantly compile it into embeddings and store it in ChromaDB. The agent will retrieve it on subsequent quizzes.")
            custom_sport = st.selectbox("Sport Topic", ["Cricket", "Football", "Badminton", "Basketball", "Tennis"], key="db_custom_sport")
            custom_text = st.text_area("Enter Fact Text (Be descriptive)", placeholder="e.g. In the 2026 World Cup, team X achieved y victory by scoring Z...")
            
            if st.button("Add Fact to Vector DB"):
                if custom_text.strip():
                    try:
                        new_id = add_custom_fact(custom_sport, custom_text)
                        st.success(f"Vector stored in collection 'sports_history' with ID: {new_id}!")
                        # Force refresh
                        st.cache_resource.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to insert vector: {e}")
                else:
                    st.warning("Please input some fact text.")
        
        # Display Database Table
        if facts:
            st.markdown("### Stored Offline Embeddings")
            # Group facts by sport
            sport_filter = st.selectbox("Filter Database View by Sport", ["All"] + list(set(f["sport"] for f in facts)))
            
            filtered_facts = facts
            if sport_filter != "All":
                filtered_facts = [f for f in facts if f["sport"] == sport_filter]
                
            for fact in filtered_facts:
                st.markdown(f"""
                <div style='background: rgba(255,255,255,0.03); border-radius: 8px; padding: 12px; margin-bottom: 8px; border-left: 3px solid #10B981;'>
                    <span style='color:#10B981; font-weight:bold;'>[{fact['sport']}]</span> <code>{fact['id']}</code><br>
                    <span style='color:#E2E8F0;'>{fact['fact']}</span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.error("ChromaDB is not initialized properly.")

# -----------------
# TAB 4: DIAGNOSTICS
# -----------------
with tab_diagnostics:
    st.subheader("🔍 RAG Pipeline Auditor")
    st.write("Inspect the ground truth facts retrieved by our orchestrator and injected into the LLM system prompt.")
    
    if st.session_state.quiz_context:
        st.write(f"**Model Provider Used:** `{st.session_state.quiz_source}`")
        st.markdown("#### Retreived Context Block")
        st.code(st.session_state.quiz_context, language="markdown")
    else:
        st.info("No query context retrieved yet. Please generate a quiz from the sidebar.")
