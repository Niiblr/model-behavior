import React from 'react';
import ReactMarkdown from 'react-markdown';
import './Stages.css';

function Stage3({ synthesis }) {
  if (!synthesis || !synthesis.response) {
    return <div>No final synthesis available.</div>;
  }

  return (
    <div className="stage3-synthesis">
      <div className="markdown-content">
        <ReactMarkdown>{synthesis.response}</ReactMarkdown>
      </div>
    </div>
  );
}

export default Stage3;