# app/services.py
import httpx
import os
from dotenv import load_dotenv
from .utils import build_file_tree

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

async def get_repo_details(repo_url: str):
    """
    Fetches repo metadata and the file tree.
    Input: https://github.com/owner/repo
    """
    # 1. Parse URL to get owner and repo name
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return {"error": "Invalid URL"}
    
    owner, repo = parts[-2], parts[-1]
    
    async with httpx.AsyncClient() as client:
        # 2. Get Metadata (Stars, Description, Default Branch)
        meta_response = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=HEADERS)
        if meta_response.status_code != 200:
            raise Exception("Repository not found or private")
        
        meta_data = meta_response.json()
        default_branch = meta_data.get("default_branch", "main")

        # 3. Get File Tree (Recursive)
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        tree_response = await client.get(tree_url, headers=HEADERS)
        tree_data = tree_response.json()
        
        # 4. Convert flat tree to nested structure
        # We limit to first 500 files to avoid crashing the browser for huge repos
        files = tree_data.get("tree", [])[:500] 
        nested_tree = build_file_tree(files)

        return {
            "status": "indexed",
            "details": {
                "owner": meta_data["owner"]["login"],
                "name": meta_data["name"],
                "description": meta_data["description"],
                "stars": meta_data["stargazers_count"],
                "forks": meta_data["forks_count"],
                "avatar": meta_data["owner"]["avatar_url"],
                "default_branch": default_branch
            },
            "fileTree": nested_tree
        }