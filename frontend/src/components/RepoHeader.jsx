// src/components/RepoHeader.jsx
import React from "react";

const RepoHeader = ({ details, onChangeRepo }) => {
  return (
    <div className="repo-header">
      <div className="repo-info">
        <img src={details.avatar} alt="Owner Avatar" className="avatar" />
        <div>
          <h2>
            {details.owner} / {details.name}
          </h2>
          <p className="repo-desc">{details.description}</p>
          <div className="repo-stats">
            <span>⭐ {details.stars.toLocaleString()} Stars</span>
            <span>🍴 {details.forks.toLocaleString()} Forks</span>
          </div>
        </div>
      </div>
      <button className="change-btn" onClick={onChangeRepo}>
        Change Repo
      </button>
    </div>
  );
};

export default RepoHeader;
