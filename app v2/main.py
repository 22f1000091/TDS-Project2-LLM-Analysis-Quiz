import os
import json
import glob
import sqlite3
import subprocess
import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import pandas as pd
from dateutil import parser

# Initialize FastAPI app
app = FastAPI(title="TDS Project 2 Solver Agent")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration ---
AIPROXY_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
# Ideally, load this from os.environ
AIPROXY_TOKEN = os.environ.get("AIPROXY_TOKEN", "")

# --- Helper: LLM Client ---
async def query_llm(prompt: str, tools_schema: List[Dict] = None) -> Dict:
    """
    Sends a prompt to the LLM. If tools_schema is provided, asks for a function call.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AIPROXY_TOKEN}"
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    if tools_schema:
        payload["tools"] = tools_schema
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient() as client:
        # High timeout for complex reasoning
        response = await client.post(AIPROXY_URL, json=payload, headers=headers, timeout=30.0)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"LLM Error: {response.text}")
        
    return response.json()

# --- Tools Implementation ---
# These functions perform the actual file/data operations.

def tool_count_weekdays(filepath: str, weekday_name: str) -> str:
    """Counts occurrences of a specific weekday in a file containing dates."""
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        count = 0
        target_weekday = weekday_name.lower()
        
        # Map common names to weekday numbers if needed, or rely on dateutil
        for line in lines:
            line = line.strip()
            if not line: continue
            try:
                dt = parser.parse(line)
                # python: Monday is 0, Sunday is 6. 
                # We interpret the weekday name.
                day_name = dt.strftime("%A").lower()
                if day_name == target_weekday:
                    count += 1
            except:
                continue
        return str(count)
    except Exception as e:
        return f"Error counting weekdays: {e}"

def tool_sort_json(input_path: str, output_path: str, keys: List[str]) -> str:
    """Sorts a JSON array of objects by specified keys."""
    try:
        df = pd.read_json(input_path)
        sorted_df = df.sort_values(by=keys)
        sorted_df.to_json(output_path, orient='records', indent=4)
        return "Sorted JSON successfully."
    except Exception as e:
        return f"Error sorting JSON: {e}"

def tool_extract_markdown_headers(input_path: str, output_path: str) -> str:
    """Extracts first H1 header from each markdown file in a directory."""
    try:
        import glob
        # Find all .md files in the specific directory logic is usually needed
        # Assuming input_path is a directory or glob pattern
        files = glob.glob(os.path.join(os.path.dirname(input_path), "*.md"))
        index = {}
        
        for file in files:
            filename = os.path.basename(file)
            with open(file, 'r') as f:
                for line in f:
                    if line.strip().startswith("# "):
                        title = line.strip()[2:].strip()
                        index[filename] = title
                        break
        
        with open(output_path, 'w') as f:
            json.dump(index, f, indent=4)
        return "Extracted headers successfully."
    except Exception as e:
        return f"Error extracting headers: {e}"

def tool_format_file(filepath: str) -> str:
    """Formats a file using prettier."""
    try:
        # Check if prettier is installed
        subprocess.run(["prettier", "--version"], check=True, capture_output=True)
        subprocess.run(["prettier", "--write", filepath], check=True)
        return f"Formatted {filepath} using Prettier."
    except subprocess.CalledProcessError as e:
        return f"Prettier failed: {e}"
    except Exception as e:
        return f"Error formatting: {e}"

# --- Tool Definitions for LLM ---
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "count_weekdays",
            "description": "Count how many times a specific day of the week appears in a date file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the input file (e.g., /data/dates.txt)"},
                    "weekday_name": {"type": "string", "description": "The day to count (e.g., Wednesday)"}
                },
                "required": ["filepath", "weekday_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sort_json",
            "description": "Sort a JSON file containing a list of objects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_path": {"type": "string", "description": "Input JSON file path"},
                    "output_path": {"type": "string", "description": "Output JSON file path"},
                    "keys": {"type": "array", "items": {"type": "string"}, "description": "List of keys to sort by"}
                },
                "required": ["input_path", "output_path", "keys"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_file",
            "description": "Format a file using Prettier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "File to format"}
                },
                "required": ["filepath"]
            }
        }
    }
    # Add other tools (logs, email extraction, etc.) here as per full assignment specs
]

# --- Main API Endpoint ---

@app.post("/api")
async def run_task(
    question: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """
    Receives a task/question.
    1. Saves uploaded file (if any).
    2. Asks LLM which tool to use.
    3. Executes the tool.
    4. Returns the result.
    """
    
    # 1. Handle File Upload
    if file:
        file_location = f"/data/{file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(await file.read())
        # Append file info to question to help LLM context
        question += f" (File saved to {file_location})"

    # 2. Query LLM for Tool Selection
    try:
        llm_resp = await query_llm(question, tools_schema=TOOLS_SCHEMA)
        choice = llm_resp["choices"][0]["message"]
        
        # If no tool called, return the content directly (simple QA)
        if "tool_calls" not in choice or not choice["tool_calls"]:
            return {"answer": choice.get("content", "I could not determine the task.")}
            
        tool_call = choice["tool_calls"][0]
        func_name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])
        
        # 3. Execute Tool
        result = ""
        if func_name == "count_weekdays":
            result = tool_count_weekdays(args["filepath"], args["weekday_name"])
        elif func_name == "sort_json":
            result = tool_sort_json(args["input_path"], args["output_path"], args["keys"])
        elif func_name == "format_file":
            result = tool_format_file(args["filepath"])
        else:
            result = "Tool not implemented."
            
        # 4. Return Answer
        return {"answer": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
