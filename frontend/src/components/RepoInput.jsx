import React, { useState } from "react";

const RepoInput = ({ onRepoSubmit, isLoading }) => {
  const [url, setUrl] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url) onRepoSubmit(url);
  };

  return (
    <div className="repo-input-container">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Paste GitHub Repository URL (e.g., https://github.com/flask/flask)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? "Indexing..." : "Load Repo"}
        </button>
      </form>
    </div>
  );
};

export default RepoInput;
