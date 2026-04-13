import uvicorn
import os

if __name__ == "__main__":
    # Ensure database directories exist before starting
    from config import DB_DIR, LEARNING_DIR, CHATS_DIR

    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(LEARNING_DIR, exist_ok=True)
    os.makedirs(CHATS_DIR, exist_ok=True)

    print("Starting J.A.R.V.I.S. Server on http://localhost:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
