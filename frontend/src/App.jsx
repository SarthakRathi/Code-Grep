// src/App.jsx
import React, { useState } from "react";
import RepoInput from "./components/RepoInput";
import SearchBar from "./components/SearchBar";
import ResultCard from "./components/ResultCard";
import FileTree from "./components/FileTree";
import RepoHeader from "./components/RepoHeader";
import { processRepository, searchCode } from "./services/api";
import "./App.css";

function App() {
  const [repoData, setRepoData] = useState(null); // Stores tree & details
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);

  const handleRepoSubmit = async (url) => {
    setLoading(true);
    try {
      const data = await processRepository(url);
      setRepoData(data); // Save the mock data
    } catch (error) {
      console.error("Error loading repo");
    }
    setLoading(false);
  };

  const handleChangeRepo = () => {
    setRepoData(null); // Reset state to go back to input screen
    setResults([]);
  };

  const handleSearch = async (query) => {
    setLoading(true);
    const data = await searchCode(query);
    setResults(data);
    setLoading(false);
  };

  return (
    <div className="app-container">
      {!repoData ? (
        // STATE 1: No Repo Loaded
        <div className="center-screen">
          <h1>Smart Grep 🧠</h1>
          <RepoInput onRepoSubmit={handleRepoSubmit} isLoading={loading} />
        </div>
      ) : (
        // STATE 2: Dashboard Layout
        <div className="dashboard-grid">
          {/* LEFT SIDEBAR */}
          <aside className="sidebar">
            <FileTree data={repoData.fileTree} />
          </aside>

          {/* RIGHT MAIN CONTENT */}
          <main className="main-content">
            <RepoHeader
              details={repoData.details}
              onChangeRepo={handleChangeRepo}
            />

            <div className="search-section">
              <SearchBar onSearch={handleSearch} />
              {loading && (
                <div className="spinner">Searching vector database...</div>
              )}
            </div>

            <div className="results-list">
              {results.map((res) => (
                <ResultCard key={res.id} result={res} />
              ))}
            </div>
          </main>
        </div>
      )}
    </div>
  );
}

export default App;
