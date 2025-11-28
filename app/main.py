import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.agent import run_agent

app = FastAPI()

# Configuration
STUDENT_EMAIL = "your_email@example.com"
STUDENT_SECRET = os.getenv("STUDENT_SECRET", "default_secret_if_testing_locally")

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

@app.post("/solve")
async def solve_quiz(request: QuizRequest, background_tasks: BackgroundTasks):
    """
    Receives the quiz task. Returns 200 immediately and solves in background.
    """
    # 1. Verify Secret
    if request.secret != STUDENT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Secret")

    # 2. Trigger the Agent in Background
    # We pass the URL and the user's credentials to the agent
    background_tasks.add_task(
        run_agent, 
        task_url=request.url, 
        email=request.email, 
        secret=request.secret
    )

    return {"message": "Agent started", "status": "ok"}