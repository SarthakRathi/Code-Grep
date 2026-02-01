import React, { useState } from "react";
import "./SearchBar.css";

const SearchBar = ({ onSearch }) => {
  const [query, setQuery] = useState("");
  const [activeModel, setActiveModel] = useState("minilm"); // Default state

  const handleSearch = () => {
    if (query) {
      console.log("Sending search:", query, activeModel);
      onSearch(query, activeModel);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="search-bar-container">
      {/* Model Selector */}
      <div className="model-selector">
        <button
          className={`model-chip ${activeModel === "bm25" ? "active" : ""}`}
          onClick={() => setActiveModel("bm25")}
        >
          ⚡ BM25
        </button>
        <button
          className={`model-chip ${activeModel === "minilm" ? "active" : ""}`}
          onClick={() => setActiveModel("minilm")}
        >
          🧠 MiniLM
        </button>
        <button
          className={`model-chip ${activeModel === "codebert" ? "active" : ""}`}
          onClick={() => setActiveModel("codebert")}
        >
          🤖 CodeBERT
        </button>
      </div>

      <div className="input-wrapper">
        <input
          type="text"
          className="search-input"
          placeholder={`Search using ${activeModel}...`}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="search-btn" onClick={handleSearch}>
          Search
        </button>
      </div>
    </div>
  );
};

export default SearchBar;
