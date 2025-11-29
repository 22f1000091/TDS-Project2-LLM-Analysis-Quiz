import os
import json
import requests
import asyncio
import google.generativeai as genai
from app.scraper import scrape_task_page
from app.tools import download_file, run_python_analysis, list_files

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Define Tools for Gemini
tools_map = {
    "download_file": download_file,
    "run_python_analysis": run_python_analysis,
    "list_files": list_files
}

def call_tools(function_call):
    """Helper to execute the tool requested by Gemini"""
    fn_name = function_call.name
    fn_args = function_call.args
    
    if fn_name in tools_map:
        # Convert args to dict
        args = {key: val for key, val in fn_args.items()}
        print(f"Agent Calling: {fn_name} with {args}")
        return tools_map[fn_name](**args)
    return "Unknown tool"

async def run_agent(task_url, email, secret):
    print(f"Starting Agent for: {task_url}")
    
    # 1. Scrape the page
    page_data = await scrape_task_page(task_url)
    print(f"Page Content: {page_data['text'][:200]}...") 

    # 2. Initialize Gemini
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        tools=[download_file, run_python_analysis, list_files]
    )
    chat = model.start_chat(enable_automatic_function_calling=True)

    # 3. FIXED PROMPT: Explicitly ask for the submit_url
    prompt = f"""
    You are an autonomous data analyst. 
    1. Read this task description:
    ---
    {page_data['text']}
    ---
    2. Available Links: {page_data['links']}
    
    Your Goal: Solve the question AND find the submission URL.
    
    Steps:
    1. If there is a file link (CSV, PDF, etc.), use `download_file`.
    2. If you have a file, write Python Pandas code to analyze it using `run_python_analysis`.
       - IMPORTANT: Your python code must save the final result into a variable named `answer`.
    3. Find the URL mentioned in the text where the answer should be posted (e.g. "Post your answer to...").
    4. Output a valid JSON object strictly in this format:
       {{ "answer": YOUR_ANSWER_HERE, "submit_url": "THE_SUBMISSION_URL_HERE" }}
    """

    try:
        response = chat.send_message(prompt)
        final_text = response.text
        
        print("Agent Result:", final_text)
        
        # 5. Extract JSON
        clean_json = final_text.replace("```json", "").replace("```", "").strip()
        answer_json = json.loads(clean_json)
        
        # 6. Submit Answer
        # FIX: Fail loudly if the LLM didn't find the URL, instead of using a fake one
        if "submit_url" not in answer_json:
            raise ValueError("LLM failed to find the submission URL in the text.")
            
        submit_url = answer_json["submit_url"]
        
        submission_payload = {
            "email": email,
            "secret": secret,
            "url": task_url,
            "answer": answer_json.get("answer")
        }

        print(f"Submitting to {submit_url}: {submission_payload}")
        
        # Uncomment to actually submit
        requests.post(submit_url, json=submission_payload) 

    except Exception as e:
        print(f"Agent Failed: {e}")
