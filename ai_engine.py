import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

_cached_model_id = None

def get_client():
    key = os.getenv("GEMINI_API_KEY")
    if key and key != "your_google_gemini_api_key_here":
        return genai.Client(api_key=key)
    return genai.Client()

def get_model_id(client):
    global _cached_model_id
    if _cached_model_id:
        return _cached_model_id
    
    print("Fetching available models...")
    models = list(client.models.list())
    
    print("Available Models:")
    valid_models = []
    
    for m in models:
        print(f"- {m.name}")
        supported = getattr(m, 'supported_actions', [])
        
        if supported and 'generateContent' in supported:
            name_lower = m.name.lower()
            if 'gemini' in name_lower and 'embedding' not in name_lower and 'audio' not in name_lower and 'tts' not in name_lower:
                valid_models.append(m.name)
                
    if not valid_models:
        raise ValueError("No valid text-generation model found.")
        
    selected_model = valid_models[0]
    for vm in valid_models:
        if 'flash' in vm.lower() and 'lite' not in vm.lower() and 'preview' not in vm.lower():
            selected_model = vm
            break
            
    _cached_model_id = selected_model
    print(f"\nAutomatically selected model: {_cached_model_id}")
    return _cached_model_id

def fetch_questions(domain, skills, diff, q_type, count):
    prompt = f"""
    Act as an interviewer. Create {count} {diff} interview questions for a {q_type} interview.
    Role: {domain}. Skills: {skills}.
    Return ONLY a numbered list of questions in plain text. Do not use any markdown formatting or introductory text.
    """
    
    try:
        client = get_client()
        response = client.models.generate_content(
            model=get_model_id(client),
            contents=prompt
        )
        
        questions = []
        for line in response.text.strip().split('\n'):
            line = line.strip()
            if line and line[0].isdigit():
                q = line.split('.', 1)[-1].strip()
                questions.append(q)
                
        if not questions:
            questions = [q.strip() for q in response.text.strip().split('\n') if q.strip()]
            
        return questions
    except Exception as e:
        print(f"Error fetching questions: {str(e)}")
        return []

def check_answer(question, answer):
    prompt = f"""
    Evaluate this interview answer in plain text.
    Question: "{question}"
    Answer: "{answer}"
    
    Make sure to explicitly include:
    - Score out of 10
    - Feedback
    - Suggestion for improvement
    - Ideal answer
    """
    
    try:
        client = get_client()
        response = client.models.generate_content(
            model=get_model_id(client),
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error checking answer: {str(e)}")
        return f"Error: {str(e)}"

def get_overall_summary(qa_text):
    prompt = f"""
    Here are the candidate's questions and answers:
    {qa_text}
    
    Give a plain text summary listing 2-3 strengths and 2-3 weaknesses based on their answers.
    """
    
    try:
        client = get_client()
        response = client.models.generate_content(
            model=get_model_id(client),
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error summarizing: {str(e)}")
        return f"Error: {str(e)}"
