# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .services import get_repo_details

app = FastAPI()

# Enable CORS (allows your React app running on localhost:3000 to talk to this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace * with your frontend URL
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
        data = await get_repo_details(request.repo_url)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))