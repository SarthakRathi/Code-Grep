# app/vector_search.py
import os
import shutil
import glob
import ast
import re
from git import Repo
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import faiss
import numpy as np

print("⏳ Loading AI Models...")
model_minilm = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ AI Models Loaded.")

STORE = {
    "chunks": [],
    "bm25": None,
    "faiss_minilm": None
}

# --- 1. UTILS ---

def anglicize_name(name):
    # 'get_tasks' -> 'get tasks'
    no_under = name.replace("_", " ")
    split_camel = re.sub('([a-z])([A-Z])', r'\1 \2', no_under)
    return split_camel.lower()

def clean_docstring(docstring):
    if not docstring: return ""
    cleaned = re.sub(r'https?://\S+|www\.\S+', '', docstring)
    return " ".join(cleaned.split())

# --- 2. PARSER ---

def extract_python_functions(code, filename):
    results = []
    try:
        tree = ast.parse(code)
        lines = code.splitlines()
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                docstring = ast.get_docstring(node) or ""
                
                # Pre-process names
                english_name = anglicize_name(func_name) # "get tasks"
                clean_docs = clean_docstring(docstring)
                
                # MiniLM sees this (Broad Context)
                ai_signature = f"function {english_name}. {clean_docs}"
                
                # BM25 sees ONLY this (Strict Name)
                # We add the raw name too just in case user types "get_tasks" exactly
                bm25_tokens = f"{english_name} {func_name}"
                
                start = node.lineno - 1
                end = node.end_lineno if hasattr(node, 'end_lineno') else start + len(node.body)
                body = "\n".join(lines[start:end])
                
                results.append({
                    "name": func_name,
                    "english_name": bm25_tokens, # <--- NEW FIELD FOR BM25
                    "signature": ai_signature,   # Used for MiniLM
                    "code": body,
                    "filename": filename
                })
    except Exception as e:
        pass
    return results

# --- 3. MAIN LOGIC ---

def clone_and_process(repo_url):
    global STORE
    repo_name = repo_url.split("/")[-1]
    repo_path = f"./temp_repos/{repo_name}"

    if os.path.exists(repo_path):
        shutil.rmtree(repo_path, ignore_errors=True)
    
    try:
        Repo.clone_from(repo_url, repo_path)
    except: pass
        
    # We now have two separate lists for indexing
    minilm_corpus = [] 
    bm25_corpus = []
    metadata = []
    
    print("🚀 Scanning files...")
    for root, dirs, files in os.walk(repo_path):
        if ".git" in root or "node_modules" in root: continue
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    funcs = extract_python_functions(content, file)
                    
                    for f in funcs:
                        # 1. Feed Signature to MiniLM
                        minilm_corpus.append(f["signature"])
                        
                        # 2. Feed ONLY Name to BM25
                        bm25_corpus.append(f["english_name"])
                        
                        metadata.append(f)
                except: pass

    if not minilm_corpus: return {"error": "No functions found."}

    print(f"Indexing {len(minilm_corpus)} functions...")

    # --- INDEXING ---

    # 1. BM25 (Strict Name Only)
    # Tokenize the name string: "get tasks get_tasks" -> ['get', 'tasks', 'get_tasks']
    tokenized_bm25 = [doc.split(" ") for doc in bm25_corpus]
    STORE["bm25"] = BM25Okapi(tokenized_bm25)

    # 2. MiniLM (Full Context)
    embeddings = model_minilm.encode(minilm_corpus)
    index = faiss.IndexFlatL2(384)
    index.add(np.array(embeddings))
    STORE["faiss_minilm"] = index
    
    STORE["chunks"] = metadata
    
    return {"status": "success", "count": len(minilm_corpus)}

def search_query(query, model_type="minilm", k=5):
    global STORE
    if not STORE["chunks"]: return []
    
    results = []
    # Clean query for better matching
    clean_q = query.lower().replace("code snippet", "").replace("how to", "").strip()

    if model_type == "bm25":
        # Tokenize query for BM25
        tokenized_query = clean_q.split(" ")
        doc_scores = STORE["bm25"].get_scores(tokenized_query)
        top_n = np.argsort(doc_scores)[::-1][:k]
        
        # Normalize Score (0-100 scale)
        max_score = max([doc_scores[i] for i in top_n]) if len(top_n) > 0 else 1.0
        if max_score == 0: max_score = 1.0

        for idx in top_n:
            if doc_scores[idx] > 0:
                results.append({
                    **STORE["chunks"][idx], 
                    "score": float(doc_scores[idx] / max_score), 
                    "source_model": "BM25 (Strict Name)"
                })

    else:
        # MiniLM Logic (unchanged)
        query_vector = model_minilm.encode([clean_q])
        distances, faiss_indices = STORE["faiss_minilm"].search(np.array(query_vector), k)
        
        for i, idx in enumerate(faiss_indices[0]):
            if idx < len(STORE["chunks"]) and idx != -1:
                score = 1 / (1 + distances[0][i])
                results.append({
                    **STORE["chunks"][idx],
                    "score": float(score),
                    "source_model": "MiniLM"
                })
                
    return results