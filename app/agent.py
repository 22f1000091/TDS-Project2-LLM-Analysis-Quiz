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
    print(f"Page Content: {page_data['text'][:200]}...") # Log first 200 chars

    # 2. Initialize Gemini Model with Tools
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        tools=[download_file, run_python_analysis, list_files]
    )
    
    chat = model.start_chat(enable_automatic_function_calling=True)

    # 3. Construct Prompt
    prompt = f"""
    You are an autonomous data analyst. 
    1. Read this task description:
    ---
    {page_data['text']}
    ---
    2. Available Links: {page_data['links']}
    
    Your Goal: Solve the question in the task description.
    
    Steps:
    1. If there is a file link (CSV, PDF, etc.), use `download_file`.
    2. If you have a file, write Python Pandas code to analyze it using `run_python_analysis`.
       - IMPORTANT: Your python code must save the final result into a variable named `answer`.
    3. Once you have the answer, output a valid JSON object strictly in this format:
       {{ "answer": YOUR_ANSWER_HERE }}
    """

    # 4. Agent Loop (Simple Version)
    # Gemini 1.5 with 'enable_automatic_function_calling' handles the loop internally 
    # for tool execution, but we need to extract the final JSON.
    
    try:
        response = chat.send_message(prompt)
        final_text = response.text
        
        print("Agent Result:", final_text)
        
        # 5. Extract JSON answer
        # Clean up Markdown code blocks if present
        clean_json = final_text.replace("```json", "").replace("```", "").strip()
        answer_json = json.loads(clean_json)
        
        # 6. Submit Answer
        submission_payload = {
            "email": email,
            "secret": secret,
            "url": task_url,
            "answer": answer_json.get("answer")
        }
        
        # We assume the task description contains the submit URL, 
        # or we follow the prompt instructions which say "Post your answer to..."
        # For this logic, we'll parse the submit URL from the text or hardcode the pattern if standardized.
        # Ideally, ask LLM to extract the submit URL too.
        
        submit_url = "https://example.com/submit" # Replace with extraction logic or LLM output
        
        # Real-world fix: Ask LLM for the submission URL in the JSON
        if "submit_url" in answer_json:
            submit_url = answer_json["submit_url"]

        print(f"Submitting to {submit_url}: {submission_payload}")
        # requests.post(submit_url, json=submission_payload) # Uncomment to actually submit

    except Exception as e:
        print(f"Agent Failed: {e}")