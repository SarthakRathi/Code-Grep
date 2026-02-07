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

# --- 1. MODEL LOADER ---
print("⏳ Loading AI Models...")
# MiniLM is used for semantic search (intent)
model_minilm = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ AI Models Loaded.")

STORE = {
    "chunks": [],
    "bm25": None,
    "faiss_minilm": None
}

# --- 2. TEXT UTILS ---

def anglicize_name(name):
    """
    Converts code names to English for better AI understanding.
    'get_tasks' -> 'get tasks'
    'calculateTax' -> 'calculate Tax'
    """
    # Replace underscores
    no_under = name.replace("_", " ")
    # Split camelCase
    split_camel = re.sub('([a-z])([A-Z])', r'\1 \2', no_under)
    return split_camel.lower()

def clean_docstring(docstring):
    """
    Removes noise from docstrings.
    """
    if not docstring: return ""
    # Remove URLs
    cleaned = re.sub(r'https?://\S+|www\.\S+', '', docstring)
    # Normalize whitespace
    return " ".join(cleaned.split())

def simple_tokenize(text):
    """
    Splits text into tokens for BM25.
    """
    return text.lower().split()

# --- 3. PARSERS ---

def extract_python_functions(code, filename):
    results = []
    try:
        tree = ast.parse(code)
        lines = code.splitlines()
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                docstring = ast.get_docstring(node) or ""
                
                # --- PREPARE DATA ---
                english_name = anglicize_name(func_name) # "get tasks"
                clean_docs = clean_docstring(docstring)
                
                # Extract the full function body
                start = node.lineno - 1
                end = node.end_lineno if hasattr(node, 'end_lineno') else start + len(node.body)
                body = "\n".join(lines[start:end])
                
                # --- STRATEGY 1: MINI-LM (Semantic) ---
                # We only show the AI the "Intent" (Name + Docstring).
                # If we showed it the whole code, it might get confused by low-level logic.
                ai_signature = f"function {english_name}. {clean_docs}"
                
                # --- STRATEGY 2: BM25 (Keyword / Grep) ---
                # We show the Search Engine EVERYTHING (Name + Docstring + Body).
                # WEIGHTING: We repeat the name 3 times so matches on the name bubble to the top.
                bm25_text = f"{english_name} {english_name} {english_name} {clean_docs} {body}"
                
                results.append({
                    "name": func_name,
                    "signature": ai_signature,   # For MiniLM
                    "search_text": bm25_text,    # For BM25
                    "code": body,                # For Display
                    "filename": filename
                })
    except Exception as e:
        # Skip files that fail parsing (syntax errors, etc.)
        pass
    return results

def extract_c_style_functions(code, filename, lang="js"):
    """
    Simple fallback parser for JS/Java/Go/Dart using Regex + Brace Counting.
    """
    results = []
    lines = code.splitlines()
    
    # Regex to find function definitions
    patterns = {
        "js": r"function\s+([a-zA-Z0-9_]+)\s*\(|const\s+([a-zA-Z0-9_]+)\s*=\s*\(|class\s+([a-zA-Z0-9_]+)",
        "java": r"(?:public|private|protected|static|\s) +[\w\<\>\[\]]+\s+([a-zA-Z0-9_]+)\s*\(",
        "go": r"func\s+([a-zA-Z0-9_]+)\s*\(",
        "dart": r"[a-zA-Z0-9_<>\[\]]+\s+([a-zA-Z0-9_]+)\s*\("
    }
    pattern = patterns.get(lang, patterns["js"])
    
    for i, line in enumerate(lines):
        match = re.search(pattern, line)
        if match:
            func_name = next((m for m in match.groups() if m), "unknown")
            
            # Simple brace counting to find end of function
            if "{" in line:
                open_braces = line.count("{")
                close_braces = line.count("}")
                end_index = i
                
                for j in range(i + 1, len(lines)):
                    open_braces += lines[j].count("{")
                    close_braces += lines[j].count("}")
                    if close_braces >= open_braces and open_braces > 0:
                        end_index = j
                        break
                
                body = "\n".join(lines[i:end_index+1])
                english_name = anglicize_name(func_name)
                
                # Same strategy as Python
                ai_signature = f"function {english_name}."
                bm25_text = f"{english_name} {english_name} {english_name} {body}"
                
                results.append({
                    "name": func_name,
                    "signature": ai_signature,
                    "search_text": bm25_text,
                    "code": body,
                    "filename": filename
                })
    return results

# --- 4. MAIN LOGIC ---

def clone_and_process(repo_url):
    global STORE
    repo_name = repo_url.split("/")[-1]
    repo_path = f"./temp_repos/{repo_name}"

    # Cleanup previous clone if exists
    if os.path.exists(repo_path):
        try: shutil.rmtree(repo_path, ignore_errors=True)
        except: pass
    
    try:
        Repo.clone_from(repo_url, repo_path)
    except: pass # Assuming it exists
        
    documents_minilm = [] 
    documents_bm25 = []
    metadata = []
    
    print("🚀 Scanning files...")
    # Map extensions to parsers
    ext_map = {".py": "python", ".js": "js", ".ts": "js", ".java": "java", ".go": "go", ".dart": "dart"}

    for root, dirs, files in os.walk(repo_path):
        if ".git" in root or "node_modules" in root: continue
        
        for file in files:
            _, ext = os.path.splitext(file)
            if ext in ext_map:
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    funcs = []
                    if ext_map[ext] == "python":
                        funcs = extract_python_functions(content, file)
                    else:
                        funcs = extract_c_style_functions(content, file, ext_map[ext])
                    
                    for f in funcs:
                        # Don't index tiny empty functions
                        if len(f["code"]) < 20: continue

                        documents_minilm.append(f["signature"])
                        documents_bm25.append(f["search_text"])
                        metadata.append(f)
                except: pass

    if not documents_minilm: return {"error": "No functions found."}

    print(f"Indexing {len(documents_minilm)} functions...")

    # --- 1. BM25 INDEXING (Full Body) ---
    tokenized_corpus = [simple_tokenize(doc) for doc in documents_bm25]
    STORE["bm25"] = BM25Okapi(tokenized_corpus)

    # --- 2. MINI-LM INDEXING (Signature Only) ---
    embeddings = model_minilm.encode(documents_minilm)
    index = faiss.IndexFlatL2(384)
    index.add(np.array(embeddings))
    STORE["faiss_minilm"] = index
    
    STORE["chunks"] = metadata
    
    return {"status": "success", "count": len(documents_minilm)}

def search_query(query, model_type="minilm", k=5):
    global STORE
    if not STORE["chunks"]: return []
    
    results = []
    clean_q = query.lower().replace("code snippet", "").replace("how to", "").strip()
    
    # --- SEARCH STRATEGY 1: BM25 (Grep) ---
    if model_type == "bm25":
        tokenized_query = simple_tokenize(clean_q)
        doc_scores = STORE["bm25"].get_scores(tokenized_query)
        top_n = np.argsort(doc_scores)[::-1][:k]
        
        # Normalize Score (0% to 100%)
        max_score = max([doc_scores[i] for i in top_n]) if len(top_n) > 0 else 1.0
        if max_score == 0: max_score = 1.0

        for idx in top_n:
            if doc_scores[idx] > 0:
                results.append({
                    **STORE["chunks"][idx], 
                    "score": float(doc_scores[idx] / max_score), 
                    "source_model": "BM25 (Full Body)"
                })

    # --- SEARCH STRATEGY 2: MiniLM (Semantic) ---
    else:
        query_vector = model_minilm.encode([clean_q])
        distances, faiss_indices = STORE["faiss_minilm"].search(np.array(query_vector), k)
        
        for i, idx in enumerate(faiss_indices[0]):
            if idx < len(STORE["chunks"]) and idx != -1:
                score = 1 / (1 + distances[0][i])
                results.append({
                    **STORE["chunks"][idx],
                    "score": float(score),
                    "source_model": "MiniLM (Signature)"
                })
                
    return results