import { useState } from 'react';
import ConversationList from './ConversationList';
import { toggleTheme } from '../theme.js';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentId,
  onSelect,
  onNewConversation,
  onPing,
}) {
  const [theme, setTheme] = useState(document.documentElement.dataset.theme || 'light');

  return (
    <div className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-logo">🏛️</div>
        <div className="sidebar-brand-text">
          <h1>Model Behavior</h1>
          <span>by Niiblr</span>
        </div>
      </div>

      <div className="sidebar-actions">
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + New Conversation
        </button>
        <button
          className="ping-test-btn"
          onClick={onPing}
          title="Test configured models"
        >
          📡
        </button>
        <button
          className="theme-toggle-btn"
          onClick={() => setTheme(toggleTheme(theme))}
          title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>

      <ConversationList
        conversations={conversations}
        currentId={currentId}
        onSelect={onSelect}
      />
    </div>
  );
}
