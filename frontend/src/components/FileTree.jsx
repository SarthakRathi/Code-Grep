// src/components/FileTree.jsx
import React, { useState } from "react";

const FileNode = ({ node }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (node.type === "file") {
    return <div className="file-node">📄 {node.name}</div>;
  }

  return (
    <div className="folder-node">
      <div className="folder-label" onClick={() => setIsOpen(!isOpen)}>
        {isOpen ? "📂" : "📁"} {node.name}
      </div>
      {isOpen && (
        <div className="folder-children">
          {node.children.map((child, index) => (
            <FileNode key={index} node={child} />
          ))}
        </div>
      )}
    </div>
  );
};

const FileTree = ({ data }) => {
  return (
    <div className="file-tree">
      <h3>Explorer</h3>
      {data.map((node, index) => (
        <FileNode key={index} node={node} />
      ))}
    </div>
  );
};

export default FileTree;
