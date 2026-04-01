import streamlit as st
import os
import re
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
    q_count = st.slider("Number of Questions", 5, 10, 5)
    
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
                    else:
                        st.info(feedback)
                    
        submit_all = st.form_submit_button("Submit All Answers", type="primary")
        
    if submit_all:
        missing_answers = False
        for i in range(len(st.session_state.questions)):
            if not st.session_state.get(f"ans_{i}", "").strip():
                missing_answers = True
                break
                
        if missing_answers:
            st.warning("Please answer all questions before submitting.")
        else:
            with st.spinner("Evaluating your answers..."):
                for i, q in enumerate(st.session_state.questions):
                    user_ans = st.session_state[f"ans_{i}"]
                    result = check_answer(q, user_ans)
                    st.session_state.evals[i] = {
                        "ans": user_ans,
                        "feedback": result
                    }
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
                    qa_history += f"\nQuestion: {st.session_state.questions[idx]}\nAnswer: {ev['ans']}\n"
                
                summary_output = get_overall_summary(qa_history)
                if summary_output and not summary_output.startswith("Error"):
                    st.session_state.summary = summary_output
                else:
                    st.error(summary_output)

        if st.session_state.summary:
            st.subheader("Performance Summary")
            st.write(st.session_state.summary)

st.markdown("<br><hr><center>Built by Ayush Agarwal | AI Interview Assistant Project</center>", unsafe_allow_html=True)
