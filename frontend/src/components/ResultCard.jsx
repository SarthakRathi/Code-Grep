import React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism";

const ResultCard = ({ result }) => {
  return (
    <div className="result-card">
      <div className="result-header">
        <div className="filename">
          📄 {result.filename}
          {/* Show which model found this */}
          <span className="model-badge">{result.source_model}</span>
        </div>
        <span className="score">Match: {Math.round(result.score * 100)}%</span>
      </div>
      <SyntaxHighlighter language="dart" style={dracula} showLineNumbers={true}>
        {result.code}
      </SyntaxHighlighter>
    </div>
  );
};

export default ResultCard;
