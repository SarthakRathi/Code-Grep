# Smart Grep 🧠

**Smart Grep** is an AI-powered semantic code search engine that goes beyond simple text matching. It allows developers to search their codebase using **Natural Language**, **Exact Keywords**, or **Code Patterns** by leveraging a hybrid ensemble of three distinct search models.

---

## 🚀 Key Features

* **Hybrid Search Engine**: Switch instantly between three search modes:
    * **BM25 (Grep Mode)**: Weighted keyword search. Finds exact variable names, error codes, and logic (e.g., `json.loads`, `UserFactory`).
    * **MiniLM (Intent Mode)**: Semantic search. Understands English queries like "how to connect to database" even if the code uses different words.
    * **CodeBERT (Pattern Mode)**: Structural search. Finds implementation patterns and code-to-code similarities.
* **Smart Parsing**:
    * Uses **AST (Abstract Syntax Tree)** for Python to perfectly extract functions and docstrings.
    * Uses **Robust Brace Counting** for C-style languages (JavaScript, Java, Go, Dart) to support multi-language repos.
* **State-Aware Caching**:
    * Intelligent backend that caches repositories on disk to prevent re-cloning.
    * Instant context switching between previously loaded repositories.
* **Focus Highlighting**:
    * Returns full function context but automatically highlights the specific lines matching your query in the UI.

---

## 🛠️ Tech Stack

### **Frontend**
* **React (Vite)**: Fast, modern UI.
* **Syntax Highlighter**: `react-syntax-highlighter` for beautiful code rendering.
* **Axios**: For communicating with the FastAPI backend.

### **Backend**
* **FastAPI**: High-performance Python web framework.
* **FAISS**: Facebook AI Similarity Search for millisecond-speed vector lookups.
* **Sentence Transformers**:
    * `all-MiniLM-L6-v2` (Semantic Text)
    * `flax-sentence-embeddings/st-codesearch-distilroberta-base` (CodeBERT)
* **Rank-BM25**: For the "Ctrl+F" style keyword search.
* **GitPython**: For cloning and managing repositories.

---

## 📦 Installation & Setup

### Prerequisites
* Node.js (v16+)
* Python (v3.9+)
* Git

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/smart-grep.git
cd smart-grep
```

### 2. Backend Setup
Navigate to the server directory and install dependencies.

```bash
cd backend
# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install fastapi uvicorn sentence-transformers rank-bm25 faiss-cpu gitpython numpy
```

Run the Server:
```bash
# Starts the API on http://127.0.0.1:8000
uvicorn main:app --reload
```

**Note**: The first run will take a few moments to download the AI models (~400MB).

### 3. Frontend Setup
Open a new terminal and navigate to the client directory.

```bash
cd frontend
npm install
```

Run the UI:
```bash
npm run dev
```

Open http://localhost:5173 in your browser.

---

## 📖 How It Works

Smart Grep processes code in three "Views" to ensure you always find what you need:

| Model | What it sees (The Index) | Best For... |
|-------|--------------------------|-------------|
| BM25 | `get_tasks` `get_tasks` [Full Code Body] | **Specifics.** Finding variable names, exact error strings, or specific library usage (e.g., `requests.get`). |
| MiniLM | "function get tasks. returns list of items." | **Intent.** Searching "fetch todo list" will find `get_tasks` because the meaning matches. |
| CodeBERT | `def get_tasks(req): ... return JsonResponse` | **Structure.** Finding "API endpoints that return JSON" based on code syntax patterns. |

---

## 📂 Project Structure

```
smart-grep/
├── backend/
│   ├── app/
│   │   ├── main.py          # API Endpoints
│   │   ├── vector_search.py # The Core Logic (Parsing + Indexing)
│   │   └── utils.py         # Helper functions
│   ├── temp_repos/          # Cached repositories (Git ignored)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React Components (RepoInput, ResultCard)
│   │   ├── services/        # API calls
│   │   └── App.jsx          # Main UI State
│   └── package.json
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repo.
2. Create a feature branch (`git checkout -b feature/NewParser`).
3. Commit your changes.
4. Push to the branch.
5. Open a Pull Request.
