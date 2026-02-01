import React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism";

const ResultCard = ({ result }) => {
  return (
    <div className="result-card">
      <div className="result-header">
        <span className="filename">📄 {result.filename}</span>
        <span className="score">
          Relevance: {Math.round(result.score * 100)}%
        </span>
      </div>
      <SyntaxHighlighter
        language="python"
        style={dracula}
        showLineNumbers={true}
      >
        {result.code}
      </SyntaxHighlighter>
    </div>
  );
};

export default ResultCard;
