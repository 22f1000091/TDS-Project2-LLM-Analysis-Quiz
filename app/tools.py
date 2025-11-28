import os
import requests
import pandas as pd
import uuid

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_file(url: str):
    """Downloads a file from a URL and returns the local filename."""
    try:
        response = requests.get(url)
        # Extract filename from URL or generate unique one
        filename = url.split("/")[-1]
        if "." not in filename: 
            filename = f"data_{uuid.uuid4().hex[:8]}.csv"
            
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(response.content)
        return f"File downloaded to: {filepath}"
    except Exception as e:
        return f"Error downloading: {str(e)}"

def run_python_analysis(code: str):
    """
    Executes a string of Python code. 
    The code must define a variable 'answer' which will be returned.
    """
    # Security Warning: specific to this contest context only.
    # In production, use a sandboxed environment (e.g., E2B).
    
    local_scope = {"pd": pd, "result": None}
    
    # Wrap code to ensure it runs
    try:
        exec(code, {}, local_scope)
        # We expect the code to set a variable named 'answer'
        if "answer" in local_scope:
            return str(local_scope["answer"])
        else:
            return "Code ran but no 'answer' variable was set."
    except Exception as e:
        return f"Execution Error: {str(e)}"

def list_files():
    """Lists files in the download directory."""
    return os.listdir(DOWNLOAD_DIR)