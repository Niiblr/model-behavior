import React from 'react';
import './ConversationList.css';

function ConversationList({ conversations, currentId, onSelect }) {
  return (
    <div className="conversation-list">
      {conversations.length === 0 ? (
        <div className="no-conversations">
          <p>No conversations yet</p>
          <p style={{ fontSize: '12px', color: '#666' }}>
            Create a new one to get started!
          </p>
        </div>
      ) : (
        conversations.map((conv) => (
          <div
            key={conv.id}
            className={`conversation-item ${conv.id === currentId ? 'active' : ''}`}
            onClick={() => onSelect(conv.id)}
          >
            <div className="conversation-title">{conv.title}</div>
            <div className="conversation-meta">
              {conv.message_count} message{conv.message_count !== 1 ? 's' : ''}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

export default ConversationList;