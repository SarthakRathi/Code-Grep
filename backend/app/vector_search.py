# app/vector_search.py
import os
import shutil
import glob
import stat
import time
from git import Repo
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import faiss
import numpy as np

# --- 1. MODEL LOADER ---
print("⏳ Loading AI Models...")
model_minilm = SentenceTransformer('all-MiniLM-L6-v2')
# We use a smaller CodeBERT to prevent memory crashes
model_codebert = SentenceTransformer('krlvi/sentence-t5-base-nlpl-code_search_net') 
print("✅ AI Models Loaded.")

STORE = {
    "chunks": [],
    "bm25": None,
    "faiss_minilm": None,
    "faiss_codebert": None
}

# --- WINDOWS PERMISSION FIX ---
def on_rm_error(func, path, exc_info):
    """
    Error handler for shutil.rmtree.
    If the file is read-only (Windows git issue), change it to writable and try again.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clone_and_process(repo_url):
    global STORE
    
    repo_name = repo_url.split("/")[-1]
    repo_path = f"./temp_repos/{repo_name}"
    
    # 1. ROBUST CLEANUP (Fixes the "Access Denied" error)
    if os.path.exists(repo_path):
        print(f"Cleaning up {repo_path}...")
        try:
            shutil.rmtree(repo_path, onerror=on_rm_error)
        except Exception as e:
            print(f"⚠️ Warning: Could not fully clean path: {e}")
            # If we can't delete it, we assume it's already there and valid
            pass 
    
    # 2. CLONE (Only if not exists)
    if not os.path.exists(repo_path):
        print(f"Cloning {repo_url}...")
        Repo.clone_from(repo_url, repo_path)
    
    # 3. READ FILES (Added .dart and .go)
    # We also ignore common build/test folders to improve quality
    extensions = [
        "**/*.py", "**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", 
        "**/*.java", "**/*.cpp", "**/*.dart", "**/*.go", "**/*.rs"
    ]
    
    code_files = []
    for ext in extensions:
        # Recursive glob search
        found = glob.glob(f"{repo_path}/{ext}", recursive=True)
        code_files.extend(found)
        
    documents = [] 
    metadata = []
    
    print(f"Found {len(code_files)} code files. Processing...")

    for file_path in code_files:
        # Skip "Generated" or "Build" files (improves accuracy)
        if "build" in file_path or ".g.dart" in file_path or "node_modules" in file_path:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Chunking Logic
            raw_chunks = content.split("\n\n")
            for chunk in raw_chunks:
                # Filter out tiny chunks (imports, braces)
                if len(chunk) < 50: continue
                
                documents.append(chunk)
                metadata.append({
                    "id": len(metadata),
                    "filename": os.path.relpath(file_path, repo_path),
                    "code": chunk
                })
        except: continue # Skip binary/error files

    if not documents: 
        return {"error": "No valid code files found (checked py, js, java, dart, etc.)"}

    # --- INDEXING ---
    print(f"Indexing {len(documents)} chunks...")

    # 1. BM25
    tokenized_corpus = [doc.split(" ") for doc in documents]
    STORE["bm25"] = BM25Okapi(tokenized_corpus)

    # 2. MiniLM
    embeddings_a = model_minilm.encode(documents)
    index_a = faiss.IndexFlatL2(384)
    index_a.add(np.array(embeddings_a))
    STORE["faiss_minilm"] = index_a

    # 3. CodeBERT
    embeddings_b = model_codebert.encode(documents)
    index_b = faiss.IndexFlatL2(768)
    index_b.add(np.array(embeddings_b))
    STORE["faiss_codebert"] = index_b
    
    STORE["chunks"] = metadata
    print("✅ Indexing Complete.")
    
    return {"status": "success", "count": len(documents)}

def search_query(query, model_type="minilm", k=5):
    global STORE
    if not STORE["chunks"]: return []
    
    results = []

    # STRATEGY 1: Keyword Search (BM25)
    if model_type == "bm25":
        tokenized_query = query.split(" ")
        doc_scores = STORE["bm25"].get_scores(tokenized_query)
        top_n = np.argsort(doc_scores)[::-1][:k]
        
        for idx in top_n:
            if doc_scores[idx] > 0:
                results.append({
                    **STORE["chunks"][idx],
                    "score": float(doc_scores[idx])
                })

    # STRATEGY 2 & 3: Vector Search
    else:
        if model_type == "codebert":
            model = model_codebert
            index = STORE["faiss_codebert"]
        else:
            model = model_minilm
            index = STORE["faiss_minilm"]

        query_vector = model.encode([query])
        distances, faiss_indices = index.search(np.array(query_vector), k)
        
        for i, idx in enumerate(faiss_indices[0]):
            if idx < len(STORE["chunks"]) and idx != -1:
                score = 1 / (1 + distances[0][i])
                results.append({
                    **STORE["chunks"][idx],
                    "score": float(score)
                })
                
    return results