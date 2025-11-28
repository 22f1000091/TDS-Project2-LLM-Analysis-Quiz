import logging
import os
import shutil

# 1. Configure Logging
# We want to see logs in the console to debug the Agent's thought process
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LLM_Solver")

# 2. Cleanup Function
def cleanup_downloads(folder="downloads"):
    """
    Removes all files in the downloads directory to keep the container clean.
    Call this after a task is finished.
    """
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")