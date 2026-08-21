import React, { useState, useRef, useEffect } from 'react';
import './Header.css';

function Header({
  title,
  hasMessages,
  onRename,
  onExportMarkdown,
  onExportHtml,
  onClear,
  onDelete,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  // Close the overflow menu on outside click / Escape
  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    const handleKey = (e) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [menuOpen]);

  const startRename = () => {
    setDraftTitle(title || '');
    setIsEditing(true);
  };

  const commitRename = () => {
    const trimmed = draftTitle.trim();
    if (trimmed && trimmed !== title) {
      onRename(trimmed);
    }
    setIsEditing(false);
  };

  const cancelRename = () => {
    setIsEditing(false);
    setDraftTitle('');
  };

  return (
    <header className="chat-header">
      <div className="chat-header-title">
        {isEditing ? (
          <div className="title-edit-row">
            <input
              ref={inputRef}
              type="text"
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') commitRename();
                if (e.key === 'Escape') cancelRename();
              }}
              maxLength={80}
            />
            <button className="hdr-btn hdr-btn-save" onClick={commitRename} title="Save title">
              Save
            </button>
            <button className="hdr-btn" onClick={cancelRename} title="Cancel">
              Cancel
            </button>
          </div>
        ) : (
          <button
            className="title-display"
            onClick={startRename}
            title="Click to rename"
          >
            <span className="title-text">{title || 'Conversation'}</span>
            <span className="title-edit-hint">✎</span>
          </button>
        )}
      </div>

      {hasMessages && (
        <div className="chat-header-actions" ref={menuRef}>
          <button
            className={`hdr-menu-btn ${menuOpen ? 'open' : ''}`}
            onClick={() => setMenuOpen(!menuOpen)}
            title="Conversation actions"
          >
            ⋯
          </button>
          {menuOpen && (
            <div className="hdr-menu">
              <button
                className="hdr-menu-item"
                onClick={() => {
                  setMenuOpen(false);
                  onExportMarkdown();
                }}
              >
                📥 Export Markdown
              </button>
              <button
                className="hdr-menu-item"
                onClick={() => {
                  setMenuOpen(false);
                  onExportHtml();
                }}
              >
                🌐 Export HTML
              </button>
              <div className="hdr-menu-divider" />
              <button
                className="hdr-menu-item danger"
                onClick={() => {
                  setMenuOpen(false);
                  onClear();
                }}
              >
                🗑️ Clear Messages
              </button>
              <button
                className="hdr-menu-item danger"
                onClick={() => {
                  setMenuOpen(false);
                  onDelete();
                }}
              >
                ❌ Delete Conversation
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
}

export default Header;
