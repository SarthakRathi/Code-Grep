# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .services import get_repo_details
from .vector_search import clone_and_process, search_query 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoRequest(BaseModel):
    repo_url: str

@app.get("/")
def read_root():
    return {"message": "Smart Grep Backend is Running!"}

@app.post("/process")
async def process_repo(request: RepoRequest):
    try:
        # 1. Get Visual Data (File Tree, Stars)
        metadata = await get_repo_details(request.repo_url)
        
        # 2. Trigger AI Processing (Clone & Embed)
        # Note: In production, this should be a background task (Celery/Redis)
        # because it might take 10-20 seconds.
        ai_status = clone_and_process(request.repo_url)
        
        return {**metadata, "ai_status": ai_status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/search")
def search(q: str, model: str = "minilm"):
    print(f"🔎 Searching for '{q}' using model: {model}")
    results = search_query(q, model_type=model)
    return results