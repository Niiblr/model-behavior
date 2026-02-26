import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './HybridView.css';

const PHASE_CONFIG = [
  {
    key: 'hybrid_phase1',
    label: '💬 Phase 1: Socratic',
    subtitle: 'All models form their initial understanding',
    color: '#3b82f6',
    bg: '#eff6ff',
    border: '#bfdbfe',
    multi: true,
  },
  {
    key: 'hybrid_phase2',
    label: '⚔️ Phase 2: Debate',
    subtitle: 'Models challenge and respond to each other',
    color: '#f59e0b',
    bg: '#fffbeb',
    border: '#fde68a',
    multi: true,
  },
  {
    key: 'hybrid_phase3',
    label: '😈 Phase 3: Devil\'s Advocate',
    subtitle: 'The consensus is challenged head-on',
    color: '#ef4444',
    bg: '#fef2f2',
    border: '#fecaca',
    multi: false,
  },
  {
    key: 'hybrid_phase4',
    label: '✨ Phase 4: Final Synthesis',
    subtitle: 'Chairman delivers the definitive answer',
    color: '#10b981',
    bg: '#f0fdf4',
    border: '#a7f3d0',
    multi: false,
  },
];

function ModelTabs({ responses }) {
  const [activeTab, setActiveTab] = useState(0);
  if (!responses || responses.length === 0) return null;

  return (
    <div className="hybrid-tabs">
      <div className="hybrid-tab-bar">
        {responses.map((r, i) => (
          <button
            key={i}
            className={`hybrid-tab-btn ${i === activeTab ? 'active' : ''}`}
            onClick={() => setActiveTab(i)}
          >
            {r.model.split('/').pop() || r.model}
          </button>
        ))}
      </div>
      <div className="hybrid-tab-content">
        <div className="hybrid-model-label">{responses[activeTab].model}</div>
        <div className="hybrid-markdown">
          <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

function PhaseBlock({ phase, data, isLoading }) {
  const [isOpen, setIsOpen] = useState(true);

  const isEmpty = !data || (Array.isArray(data) && data.length === 0) ||
    (!Array.isArray(data) && !data.response);

  if (isEmpty && !isLoading) return null;

  return (
    <div
      className="hybrid-phase-block"
      style={{ borderColor: phase.border, backgroundColor: phase.bg }}
    >
      <button
        className="hybrid-phase-header"
        onClick={() => setIsOpen(!isOpen)}
        style={{ color: phase.color }}
      >
        <span className="hybrid-phase-title">{phase.label}</span>
        <span className="hybrid-phase-subtitle">{phase.subtitle}</span>
        <span className="hybrid-phase-toggle">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div className="hybrid-phase-body">
          {isLoading && isEmpty ? (
            <div className="hybrid-loading">
              <div className="hybrid-spinner" style={{ borderTopColor: phase.color }} />
              <span style={{ color: phase.color }}>Models are thinking...</span>
            </div>
          ) : phase.multi ? (
            <ModelTabs responses={data} />
          ) : (
            <div>
              <div className="hybrid-model-label">{data.model}</div>
              <div className="hybrid-markdown">
                <ReactMarkdown>{data.response}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HybridView({ message, loadingPhase }) {
  return (
    <div className="hybrid-view">
      <div className="hybrid-header">
        <span className="hybrid-badge">🔀 Debate Mode</span>
        <span className="hybrid-header-sub">Socratic → Debate → Devil's Advocate → Synthesis</span>
      </div>

      {PHASE_CONFIG.map((phase) => {
        const data = message[phase.key];
        const isLoading = loadingPhase === phase.key;
        return (
          <PhaseBlock
            key={phase.key}
            phase={phase}
            data={data}
            isLoading={isLoading}
          />
        );
      })}
    </div>
  );
}

export default HybridView;