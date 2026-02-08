import React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism";

const ResultCard = ({ result, query }) => {
  // Accept 'query' prop

  // Helper to find the "best matching line" for scrolling/highlighting
  const getHighlightLines = (code, query) => {
    if (!query) return [];
    const lines = code.split("\n");
    const queryWords = query.toLowerCase().split(" ");
    const matchingLineNumbers = [];

    lines.forEach((line, index) => {
      // simple check: does this line contain query words?
      const lowerLine = line.toLowerCase();
      if (queryWords.some((w) => lowerLine.includes(w) && w.length > 2)) {
        matchingLineNumbers.push(index + 1); // 1-based index
      }
    });
    return matchingLineNumbers;
  };

  const highlights = getHighlightLines(result.code, query);

  return (
    <div className="result-card">
      <div className="result-header">
        <div className="filename">
          📄 {result.filename}
          <span className="model-badge">{result.source_model}</span>
        </div>
        <span className="score">Match: {Math.round(result.score * 100)}%</span>
      </div>

      <SyntaxHighlighter
        language="python"
        style={dracula}
        showLineNumbers={true}
        wrapLines={true}
        lineProps={(lineNumber) => {
          const isMatch = highlights.includes(lineNumber);
          return {
            style: {
              display: "block",
              backgroundColor: isMatch ? "rgba(255, 255, 0, 0.2)" : undefined, // Yellow highlight
              borderLeft: isMatch ? "3px solid #ffcc00" : undefined,
            },
          };
        }}
      >
        {result.code}
      </SyntaxHighlighter>
    </div>
  );
};

export default ResultCard;
