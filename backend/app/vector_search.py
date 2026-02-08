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

# Model A: MiniLM (Good at English "Intent")
model_minilm = SentenceTransformer('all-MiniLM-L6-v2')

# Model B: CodeBERT (Good at "Code Structure" and "Language-to-Code")
model_codebert = SentenceTransformer('flax-sentence-embeddings/st-codesearch-distilroberta-base')

print("✅ AI Models Loaded.")

STORE = {
    "chunks": [],
    "bm25": None,
    "faiss_minilm": None,
    "faiss_codebert": None,
    "current_repo": None
}

# --- 2. UTILS ---

def anglicize_name(name):
    """ 'get_tasks' -> 'get tasks' """
    no_under = name.replace("_", " ")
    split_camel = re.sub('([a-z])([A-Z])', r'\1 \2', no_under)
    return split_camel.lower()

def clean_docstring(docstring):
    if not docstring: return ""
    cleaned = re.sub(r'https?://\S+|www\.\S+', '', docstring)
    return " ".join(cleaned.split())

def simple_tokenize(text):
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
                
                # Data Prep
                english_name = anglicize_name(func_name)
                clean_docs = clean_docstring(docstring)
                
                start = node.lineno - 1
                end = node.end_lineno if hasattr(node, 'end_lineno') else start + len(node.body)
                body = "\n".join(lines[start:end])
                short_body = "\n".join(lines[start:start+5]) 
                
                # 3-View Indexing Strategy
                ai_signature = f"function {english_name}. {clean_docs}"
                bm25_text = f"{english_name} {english_name} {english_name} {clean_docs} {body}"
                codebert_text = f"{short_body} ... {clean_docs}"
                
                results.append({
                    "name": func_name,
                    "signature": ai_signature,
                    "codebert_text": codebert_text,
                    "search_text": bm25_text,
                    "code": body,
                    "filename": filename
                })
    except: pass
    return results

def extract_c_style_functions(code, filename, lang="js"):
    """ Regex-based parser for JS, Java, Go, Dart """
    results = []
    lines = code.splitlines()
    
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
            
            # Simple brace counting
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
                
                ai_signature = f"function {english_name}."
                bm25_text = f"{english_name} {english_name} {english_name} {body}"
                short_body = "\n".join(lines[i:i+5])
                codebert_text = f"{short_body} ..."

                results.append({
                    "name": func_name,
                    "signature": ai_signature,
                    "codebert_text": codebert_text,
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
    
    # Check if we already have this repo loaded
    if STORE.get("current_repo") == repo_name:
        print(f"✅ {repo_name} is already active. Skipping.")
        return {"status": "cached", "count": len(STORE["chunks"])}

    print(f"🔄 Switching context to: {repo_name}...")
    
    # RESET STORE
    STORE = {
        "chunks": [],
        "bm25": None,
        "faiss_minilm": None,
        "faiss_codebert": None,
        "current_repo": None
    }

    # Disk Cache Check
    if os.path.exists(repo_path):
        print(f"📂 Found cached files for {repo_name}.")
    else:
        print(f"⬇️ Cloning {repo_url}...")
        try:
            Repo.clone_from(repo_url, repo_path)
        except Exception as e:
            return {"error": f"Clone failed: {str(e)}"}
        
    # Re-Index
    docs_minilm = [] 
    docs_codebert = []
    docs_bm25 = []
    metadata = []
    
    print("🚀 Building Index...")
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
                        if len(f["code"]) < 20: continue 

                        docs_minilm.append(f["signature"])
                        docs_codebert.append(f["codebert_text"])
                        docs_bm25.append(f["search_text"])
                        metadata.append(f)
                except: pass

    if not docs_minilm: 
        return {"error": "No functions found."}

    print(f"📊 Indexing {len(docs_minilm)} functions...")

    tokenized_corpus = [simple_tokenize(doc) for doc in docs_bm25]
    bm25_index = BM25Okapi(tokenized_corpus)

    emb_minilm = model_minilm.encode(docs_minilm)
    index_minilm = faiss.IndexFlatL2(384)
    index_minilm.add(np.array(emb_minilm))

    emb_codebert = model_codebert.encode(docs_codebert)
    index_codebert = faiss.IndexFlatL2(768)
    index_codebert.add(np.array(emb_codebert))
    
    STORE["chunks"] = metadata
    STORE["bm25"] = bm25_index
    STORE["faiss_minilm"] = index_minilm
    STORE["faiss_codebert"] = index_codebert
    STORE["current_repo"] = repo_name
    
    print("✅ Indexing Complete.")
    return {"status": "success", "count": len(docs_minilm)}

def search_query(query, model_type="minilm", k=5):
    global STORE
    if not STORE["chunks"]: return []
    
    results = []
    clean_q = query.lower().replace("code snippet", "").replace("how to", "").strip()
    
    if model_type == "bm25":
        tokenized_query = simple_tokenize(clean_q)
        doc_scores = STORE["bm25"].get_scores(tokenized_query)
        top_n = np.argsort(doc_scores)[::-1][:k]
        
        max_score = max([doc_scores[i] for i in top_n]) if len(top_n) > 0 else 1.0
        if max_score == 0: max_score = 1.0

        for idx in top_n:
            if doc_scores[idx] > 0:
                results.append({
                    **STORE["chunks"][idx], 
                    "score": float(doc_scores[idx] / max_score), 
                    "source_model": "BM25"
                })

    else:
        if model_type == "codebert":
            model = model_codebert
            index = STORE["faiss_codebert"]
        else:
            model = model_minilm
            index = STORE["faiss_minilm"]

        query_vector = model.encode([clean_q])
        distances, faiss_indices = index.search(np.array(query_vector), k)
        
        for i, idx in enumerate(faiss_indices[0]):
            if idx < len(STORE["chunks"]) and idx != -1:
                score = 1 / (1 + distances[0][i])
                results.append({
                    **STORE["chunks"][idx],
                    "score": float(score),
                    "source_model": "CodeBERT" if model_type == "codebert" else "MiniLM"
                })
                
    return results