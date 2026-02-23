import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stages.css';

function Stage2({ rankings, labelToModel, aggregateRankings }) {
  const [activeTab, setActiveTab] = useState(0);

  // Debug: Log what we're receiving
  console.log('Stage2 Props:', { rankings, labelToModel, aggregateRankings });

  if (!rankings || rankings.length === 0) {
    return <div>No rankings available yet.</div>;
  }

  return (
    <div className="stage2">
      <h3>Stage 2: Peer Rankings</h3>
      <p style={{ fontSize: '14px', color: '#666', marginBottom: '12px' }}>
        Raw Evaluations - Each model evaluated all responses (anonymized as Response A, B, C, etc.) and provided rankings. 
        Below, model names are shown in <strong>bold</strong> for readability, but the original evaluation used anonymous labels.
      </p>
      
      <div className="stage2-tabs">
        {rankings.map((ranking, index) => (
          <button
            key={index}
            className={`stage2-tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {ranking.model}
          </button>
        ))}
      </div>
      <div className="stage2-content">
        <div className="markdown-content">
          <ReactMarkdown>{rankings[activeTab].ranking}</ReactMarkdown>
        </div>
        
        {rankings[activeTab].parsed_ranking && rankings[activeTab].parsed_ranking.length > 0 && (
          <div className="stage2-ranking">
            <h4>Extracted Ranking:</h4>
            <ul>
              {rankings[activeTab].parsed_ranking.map((label, idx) => (
                <li key={idx}>
                  {idx + 1}. {labelToModel && labelToModel[label] ? (
                    <>
                      {label} by <strong>{labelToModel[label]}</strong>
                    </>
                  ) : label}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <h4>Aggregate Rankings</h4>
          <p>Based on all peer evaluations (lower average rank = better):</p>
          {aggregateRankings.map((item, index) => (
            <div key={index} className="ranking-item">
              <span className="ranking-position">#{index + 1}</span>
              <span className="ranking-model">{item.model}</span>
              <span className="ranking-score">
                Avg: {item.average_rank.toFixed(2)} ({item.rankings_count} votes)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Stage2;