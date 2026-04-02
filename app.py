import streamlit as st
import os
import re
import time
import threading
from ai_engine import fetch_questions, check_answer, get_overall_summary
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="AI Interview Assistant", page_icon="📝", layout="wide")

if "questions" not in st.session_state:
    st.session_state.questions = []
if "evals" not in st.session_state:
    st.session_state.evals = {}
if "summary" not in st.session_state:
    st.session_state.summary = None

def reset_session():
    st.session_state.questions = []
    st.session_state.evals = {}
    st.session_state.summary = None

st.title("📝 AI Interview Assistant")
st.write("Practise for your interviews with AI!")
st.divider()

key = os.getenv("GEMINI_API_KEY")
if not key or key == "your_google_gemini_api_key_here":
    st.error("API Key is missing! Please configure GEMINI_API_KEY in your .env file.")
    st.stop()

with st.sidebar:
    st.header("Settings")
    
    domain_choice = st.selectbox("Role Domain", ["Data Science", "Web Development", "AI/ML", "General HR", "Other (Custom)"])
    if domain_choice == "Other (Custom)":
        domain = st.text_input("Enter Custom Domain", value="", placeholder="e.g. Embedded Systems")
    else:
        domain = domain_choice
        
    skills = st.text_input("Core Skills", value="Python, SQL")
    diff = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
    q_type = st.selectbox("Interview Type", ["Technical", "HR", "Behavioral"])
    q_count = st.slider("Number of Questions", 1, 10, 5)
    
    if st.button("Generate Questions", type="primary", use_container_width=True):
        if not domain.strip():
            st.error("Please enter a valid domain.")
        else:
            with st.spinner("Generating questions..."):
                reset_session()
                questions = fetch_questions(domain, skills, diff, q_type, q_count)
                if questions:
                    st.session_state.questions = questions[:q_count]
                    st.success("Ready!")
                else:
                    st.error("Failed to generate questions. Check logs.")
                
    if st.button("Start Over", use_container_width=True):
        reset_session()
        st.rerun()

if not st.session_state.questions:
    st.info("Select your preferences and generate questions to begin.")
else:
    st.subheader(f"{domain} Interview")
    
    with st.form("interview_form"):
        for i, q in enumerate(st.session_state.questions):
            with st.container(border=True):
                st.write(f"**Q{i+1}: {q}**")
                st.text_area("Your Answer:", key=f"ans_{i}", height=100)
                
                # Display evaluation feedback inside the form if it was submitted before
                if i in st.session_state.evals:
                    feedback = st.session_state.evals[i]["feedback"]
                    st.markdown("---")
                    st.markdown("### Evaluation")
                    if "Error" in feedback:
                        st.error(feedback)
                    elif feedback == "Skipped":
                        st.warning("Skipped: No answer provided.")
                    else:
                        st.info(feedback)
                    
        submit_all = st.form_submit_button("Submit All Answers", type="primary")
        
    if submit_all:
        messages = ["Analyzing your answer...", "Checking concepts...", "Almost there...", "Finalizing feedback..."]
        status_placeholder = st.empty()
        
        eval_results = {}
        questions_to_eval = list(st.session_state.questions)
        user_answers = {i: st.session_state.get(f"ans_{i}", "") for i in range(len(questions_to_eval))}
        
        def run_evals():
            for i, q in enumerate(questions_to_eval):
                user_ans = user_answers[i]
                if not user_ans.strip():
                    eval_results[i] = {
                        "ans": user_ans,
                        "feedback": "Skipped"
                    }
                else:
                    result = check_answer(q, user_ans)
                    eval_results[i] = {
                        "ans": user_ans,
                        "feedback": result
                    }
                    
        eval_thread = threading.Thread(target=run_evals)
        eval_thread.start()
        
        msg_idx = 0
        while eval_thread.is_alive():
            status_placeholder.info(f"⏳ {messages[msg_idx % len(messages)]}")
            time.sleep(1.5)
            msg_idx += 1
            
        eval_thread.join()
        status_placeholder.empty()
        
        for i, res in eval_results.items():
            st.session_state.evals[i] = res
            
        st.rerun()

    if len(st.session_state.evals) == len(st.session_state.questions) and len(st.session_state.questions) > 0:
        st.divider()
        
        total_score = 0
        valid_evals = 0
        
        for ev in st.session_state.evals.values():
            match = re.search(r'([0-9]+)\s*/\s*10', ev["feedback"])
            if match:
                total_score += float(match.group(1))
                valid_evals += 1
                
        if valid_evals > 0:
            avg_score = total_score / valid_evals
            st.header(f"Estimated Score: {avg_score:.1f}/10")
        
        if st.button("Finish Interview & Get Summary", type="primary"):
            with st.spinner("Generating summary..."):
                qa_history = ""
                for idx, ev in st.session_state.evals.items():
                    ans_text = ev['ans'] if ev['ans'].strip() else "[Skipped]"
                    qa_history += f"\nQuestion: {st.session_state.questions[idx]}\nAnswer: {ans_text}\n"
                
                summary_output = get_overall_summary(qa_history)
                if summary_output and not summary_output.startswith("Error"):
                    st.session_state.summary = summary_output
                else:
                    st.error(summary_output)

        if st.session_state.summary:
            st.subheader("Performance Summary")
            st.write(st.session_state.summary)

st.markdown("<br><hr><center>Built by Ayush Agarwal | AI Interview Assistant Project</center>", unsafe_allow_html=True)
