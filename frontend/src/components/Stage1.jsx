import { useState } from "react";
import ReactMarkdown from "react-markdown";
import "./Stages.css";

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) return null;

  return (
    <div className="stage1">
      <h3>Stage 1: Individual Responses</h3>

      <div className="stage1-tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`stage1-tab ${activeTab === index ? "active" : ""}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.model.split("/")[1] || resp.model}
          </button>
        ))}
      </div>

      <div className="stage1-content">
        <div className="model-name">{responses[activeTab].model}</div>
        <div className="response-text markdown-content">
          <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

