import os
import shutil
import glob
import stat
from git import Repo
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import faiss
import numpy as np

# --- 1. MODEL LOADER ---
print("⏳ Loading AI Models...")
model_minilm = SentenceTransformer('all-MiniLM-L6-v2')
model_codebert = SentenceTransformer('krlvi/sentence-t5-base-nlpl-code_search_net') 
print("✅ AI Models Loaded.")

STORE = {
    "chunks": [],
    "bm25": None,
    "faiss_minilm": None,
    "faiss_codebert": None
}

def on_rm_error(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except: pass

# --- THE FIX: NOISE-FILTERED CHUNKER ---
def smart_paragraph_chunker(content):
    """
    Splits by blank lines (logical paragraphs).
    Aggressively filters out 'noise' (imports, braces, tiny lines).
    Merges small chunks to ensure context.
    """
    # 1. Split by double newlines (standard developer separation)
    raw_blocks = content.split('\n\n')
    
    clean_chunks = []
    current_buffer = ""
    
    for block in raw_blocks:
        stripped = block.strip()
        
        # --- NOISE FILTERS (Skip these results) ---
        if not stripped: continue
        if stripped.startswith(("import ", "package ", "from ", "include ")): continue
        if len(stripped) < 40: # Skip tiny fragments (like "}")
            # If it's tiny, maybe append to previous, but don't make it its own result
            if current_buffer: 
                current_buffer += "\n\n" + block
            continue
            
        # --- MERGE LOGIC ---
        # If the current buffer is small (< 300 chars), keep adding to it
        # This prevents getting 5 different results for one function
        if len(current_buffer) + len(block) < 500:
            current_buffer += "\n\n" + block
        else:
            # Buffer is full, save it
            clean_chunks.append(current_buffer.strip())
            current_buffer = block # Start new buffer
            
    # Add the last piece
    if current_buffer:
        clean_chunks.append(current_buffer.strip())
        
    return clean_chunks

def clone_and_process(repo_url):
    global STORE
    print("🧹 Clearing previous repository data...")
    STORE = {
        "chunks": [],
        "bm25": None,
        "faiss_minilm": None,
        "faiss_codebert": None
    }
    repo_name = repo_url.rstrip("/").split("/")[-1]
    repo_path = f"./temp_repos/{repo_name}"
    
    if os.path.exists(repo_path):
        try: shutil.rmtree(repo_path, onerror=on_rm_error)
        except: pass
    
    try: Repo.clone_from(repo_url, repo_path)
    except Exception as e: return {"error": str(e)}
    
    extensions = ["**/*.py", "**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.java", "**/*.dart", "**/*.go", "**/*.cpp"]
    code_files = []
    for ext in extensions:
        code_files.extend(glob.glob(f"{repo_path}/{ext}", recursive=True))
        
    documents = [] 
    metadata = []
    
    print(f"Processing {len(code_files)} files with Noise Filter...")

    for file_path in code_files:
        # Filter generated files
        if any(x in file_path for x in ["build", ".g.dart", "node_modules", "test", "coverage"]):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # USE SMART PARAGRAPH CHUNKER
            chunks = smart_paragraph_chunker(content)
            
            for chunk in chunks:
                documents.append(chunk)
                metadata.append({
                    "id": len(metadata),
                    "filename": os.path.relpath(file_path, repo_path),
                    "code": chunk
                })
        except: continue

    if not documents: 
        return {"error": "No valid code files found."}

    # Indexing
    print(f"Indexing {len(documents)} high-quality chunks...")
    
    # BM25
    tokenized_corpus = [doc.split(" ") for doc in documents]
    STORE["bm25"] = BM25Okapi(tokenized_corpus)

    # MiniLM
    embeddings_a = model_minilm.encode(documents)
    index_a = faiss.IndexFlatL2(384)
    index_a.add(np.array(embeddings_a))
    STORE["faiss_minilm"] = index_a

    # CodeBERT
    embeddings_b = model_codebert.encode(documents)
    index_b = faiss.IndexFlatL2(768)
    index_b.add(np.array(embeddings_b))
    STORE["faiss_codebert"] = index_b
    
    STORE["chunks"] = metadata
    return {"status": "success", "count": len(documents)}

def search_query(query, model_type="minilm", k=5):
    global STORE
    if not STORE["chunks"]: return []
    results = []
    
    model_type = model_type.lower().strip()
    print(f"🔎 Internal Search: Query='{query}' | Model='{model_type}'")

    if model_type == "bm25":
        tokenized_query = query.split(" ")
        doc_scores = STORE["bm25"].get_scores(tokenized_query)
        top_n = np.argsort(doc_scores)[::-1][:k]
        for idx in top_n:
            if doc_scores[idx] > 0:
                results.append({**STORE["chunks"][idx], "score": float(doc_scores[idx]), "source_model": "BM25"})
    else:
        # Default / MiniLM
        model, index, badge = model_minilm, STORE["faiss_minilm"], "MiniLM"
        
        # Explicit CodeBERT
        if model_type == "codebert":
            model, index, badge = model_codebert, STORE["faiss_codebert"], "CodeBERT"

        query_vector = model.encode([query])
        distances, faiss_indices = index.search(np.array(query_vector), k)
        
        for i, idx in enumerate(faiss_indices[0]):
            if idx < len(STORE["chunks"]) and idx != -1:
                score = 1 / (1 + distances[0][i])
                results.append({**STORE["chunks"][idx], "score": float(score), "source_model": badge})
                
    return results