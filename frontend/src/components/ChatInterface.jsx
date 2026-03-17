import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import HybridView from './HybridView';
import './ChatInterface.css';

const ACCEPTED_TYPES = '.pdf,.docx,.txt,.sh,.py,.md,.xls,.xlsx';
const API_BASE = 'http://localhost:8001';

function ChatInterface({ conversationId, messages, onSendMessage, onUpdateTitle, onDelete }) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState('council');
  const [hybridLoadingPhase, setHybridLoadingPhase] = useState('');
  const [loadingStage, setLoadingStage] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [tooltip, setTooltip] = useState({ visible: false, text: '', x: 0, y: 0 });

  // File upload state
  const [attachedFile, setAttachedFile] = useState(null);   // { name, text }
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const modeTooltips = {
    council: '🏛️ Council Mode\n\nA structured 3-stage process:\n• Stage 1: Each AI model independently forms its own answer\n• Stage 2: Models evaluate and rank each other\'s responses\n• Stage 3: A Chairman AI synthesizes the best final answer',
    hybrid: '🔀 Debate Mode\n\nA dynamic 4-phase debate process:\n• Phase 1: Models form initial understanding (Socratic)\n• Phase 2: Models debate and challenge each other\n• Phase 3: A Devil\'s Advocate challenges the consensus\n• Phase 4: A Chairman delivers the final synthesis',
  };

  const conversationMode = (() => {
    const firstAssistant = messages.find(m => m.role === 'assistant');
    if (!firstAssistant) return null;
    if (firstAssistant.mode) return firstAssistant.mode;
    if (firstAssistant.stage1 || firstAssistant.stage2 || firstAssistant.stage3) return 'council';
    return null;
  })();
  const isLocked = conversationMode !== null;

  useEffect(() => {
    if (conversationMode) {
      setMode(conversationMode);
    }
  }, [conversationMode]);

  const handleTooltipShow = (e, modeKey) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      visible: true,
      text: modeTooltips[modeKey],
      x: rect.left + rect.width / 2,
      y: rect.bottom + window.scrollY + 8,
    });
  };

  const handleTooltipHide = () => {
    setTooltip({ ...tooltip, visible: false });
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    const messagesContainer = messagesEndRef.current?.parentElement;
    if (messagesContainer) {
      const isNearBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight < 100;
      if (isNearBottom || messages.length === 0) {
        scrollToBottom();
      }
    }
  }, [messages]);

  // ---- File upload ----

  const handleFileButtonClick = () => {
    if (isLoading || isUploading) return;
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input so same file can be re-selected if needed
    e.target.value = '';

    setUploadError('');
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
      }

      const data = await response.json();
      setAttachedFile({ name: data.filename, text: data.text });
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveFile = () => {
    setAttachedFile(null);
    setUploadError('');
  };

  // ---- Submit ----

  const buildMessageWithFile = (userText, file) => {
    if (!file) return userText;
    return `[File: ${file.name}]\n\`\`\`\n${file.text}\n\`\`\`\n\nUser question: ${userText}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if ((!input.trim() && !attachedFile) || isLoading || isUploading) return;

    const finalContent = buildMessageWithFile(input, attachedFile);

    setIsLoading(true);
    if (mode === 'hybrid') {
      setHybridLoadingPhase('hybrid_phase1');
    } else {
      setLoadingStage('stage1');
    }

    const fileNameForDisplay = attachedFile ? attachedFile.name : null;
    setAttachedFile(null);
    setUploadError('');

    await onSendMessage(finalContent, mode, fileNameForDisplay);
    setInput('');
    setIsLoading(false);
    setLoadingStage('');
    setHybridLoadingPhase('');
  };

  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'assistant') {
        if (lastMessage.stage3) {
          setLoadingStage('');
          setIsLoading(false);
        } else if (lastMessage.stage2 && lastMessage.stage2.length > 0) {
          setLoadingStage('stage3');
        } else if (lastMessage.stage1 && lastMessage.stage1.length > 0) {
          setLoadingStage('stage2');
        }
      }
    }
  }, [messages]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleClearMessages = async () => {
    if (!window.confirm('Are you sure you want to clear all messages? This cannot be undone.')) return;
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`, { method: 'DELETE' });
      if (response.ok) window.location.reload();
    } catch (error) {
      console.error('Error clearing messages:', error);
      alert('Failed to clear messages. Please try again.');
    }
  };

  const handleRename = async () => {
    if (!newTitle.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/title`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle }),
      });
      if (response.ok) {
        onUpdateTitle(newTitle);
        setIsRenaming(false);
        setNewTitle('');
      }
    } catch (error) {
      console.error('Error renaming conversation:', error);
      alert('Failed to rename conversation. Please try again.');
    }
  };

  const handleDeleteConversation = async () => {
    if (!window.confirm('Are you sure you want to delete this entire conversation? This cannot be undone.')) return;
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, { method: 'DELETE' });
      if (response.ok) onDelete();
    } catch (error) {
      console.error('Error deleting conversation:', error);
      alert('Failed to delete conversation. Please try again.');
    }
  };

  const handleExport = async (format = 'markdown') => {
    try {
      const url = format === 'html'
        ? `${API_BASE}/api/conversations/${conversationId}/export/html`
        : `${API_BASE}/api/conversations/${conversationId}/export`;
      const response = await fetch(url);
      const data = await response.json();
      const content = format === 'html' ? data.html : data.markdown;
      const mimeType = format === 'html' ? 'text/html' : 'text/markdown';
      const blob = new Blob([content], { type: mimeType });
      const dlUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = dlUrl;
      a.download = data.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(dlUrl);
    } catch (error) {
      console.error('Error exporting conversation:', error);
      alert('Failed to export conversation. Please try again.');
    }
  };

  const handleCopyFinalAnswer = (finalAnswer) => {
    navigator.clipboard.writeText(finalAnswer).then(() => {
      alert('Final answer copied to clipboard!');
    }).catch(err => {
      console.error('Error copying to clipboard:', err);
      alert('Failed to copy to clipboard.');
    });
  };

  const getLoadingMessage = () => {
    if (mode === 'hybrid') {
      switch (hybridLoadingPhase) {
        case 'hybrid_phase1': return '💬 Phase 1: Models are forming their initial understanding...';
        case 'hybrid_phase2': return '⚔️ Phase 2: Models are debating and challenging each other...';
        case 'hybrid_phase3': return '😈 Phase 3: Devil\'s Advocate is challenging the consensus...';
        case 'hybrid_phase4': return '✨ Phase 4: Chairman is delivering the final synthesis...';
        default: return 'Debate Mode Council is thinking...';
      }
    }
    switch (loadingStage) {
      case 'stage1': return '🤔 Stage 1: Council members are forming their initial responses...';
      case 'stage2': return '⚖️ Stage 2: Models are evaluating and ranking each other\'s responses...';
      case 'stage3': return '✨ Stage 3: Chairman is synthesizing the final answer...';
      default: return 'Processing...';
    }
  };

  const ModeBadge = ({ msgMode }) => {
    const isHybrid = msgMode === 'hybrid';
    return (
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '3px 10px',
        borderRadius: '12px',
        fontSize: '11px',
        fontWeight: 600,
        backgroundColor: isHybrid ? '#ede9fe' : '#dbeafe',
        color: isHybrid ? '#6d28d9' : '#1d4ed8',
        border: `1px solid ${isHybrid ? '#c4b5fd' : '#93c5fd'}`,
        marginBottom: '8px',
        userSelect: 'none',
      }}>
        {isHybrid ? '🔀 Debate' : '🏛️ Council'}
      </div>
    );
  };

  /** Extract the [File: …] name from a message content string, if present */
  const parseFileBadge = (content) => {
    if (!content) return null;
    const match = content.match(/^\[File: (.+?)\]/);
    return match ? match[1] : null;
  };

  /** Strip the prepended file block, returning just the user's question text */
  const parseUserText = (content) => {
    if (!content) return content;
    // If there's a file block, extract just the question part
    const questionMatch = content.match(/\nUser question: ([\s\S]*)$/);
    if (questionMatch) return questionMatch[1];
    return content;
  };

  const canSubmit = (input.trim() || attachedFile) && !isLoading && !isUploading;

  return (
    <div className="chat-interface">

      {tooltip.visible && (
        <div style={{
          position: 'fixed',
          left: tooltip.x,
          top: tooltip.y,
          transform: 'translateX(-50%)',
          backgroundColor: '#1e1e2e',
          color: '#e2e8f0',
          padding: '12px 16px',
          borderRadius: '8px',
          fontSize: '12px',
          lineHeight: '1.7',
          whiteSpace: 'pre-line',
          maxWidth: '280px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.35)',
          zIndex: 9999,
          pointerEvents: 'none',
          border: '1px solid rgba(255,255,255,0.1)',
        }}>
          {tooltip.text}
          <div style={{
            position: 'absolute',
            top: '-6px',
            left: '50%',
            transform: 'translateX(-50%)',
            width: 0,
            height: 0,
            borderLeft: '6px solid transparent',
            borderRight: '6px solid transparent',
            borderBottom: '6px solid #1e1e2e',
          }} />
        </div>
      )}

      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '10px',
        borderBottom: '1px solid #e0e0e0'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {!isRenaming ? (
            <>
              <h2 style={{ margin: 0 }}>Conversation</h2>
              <button
                onClick={() => setIsRenaming(true)}
                style={{
                  padding: '4px 8px',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '12px'
                }}
              >
                Rename
              </button>
            </>
          ) : (
            <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="New conversation title"
                style={{
                  padding: '6px 10px',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  fontSize: '14px',
                  width: '250px'
                }}
                autoFocus
              />
              <button onClick={handleRename} style={{ padding: '6px 12px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>Save</button>
              <button onClick={() => { setIsRenaming(false); setNewTitle(''); }} style={{ padding: '6px 12px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>Cancel</button>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          {messages.length > 0 && (
            <>
              <button onClick={() => handleExport('markdown')} style={{ padding: '8px 16px', backgroundColor: '#17a2b8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '14px' }} title="Export as Markdown">📥 Export MD</button>
              <button onClick={() => handleExport('html')} style={{ padding: '8px 16px', backgroundColor: '#6f42c1', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '14px' }} title="Export as HTML">🌐 Export HTML</button>
              <button onClick={handleClearMessages} style={{ padding: '8px 16px', backgroundColor: '#ffc107', color: '#333', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '14px' }} title="Clear all messages">🗑️ Clear</button>
              <button onClick={handleDeleteConversation} style={{ padding: '8px 16px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '14px' }} title="Delete entire conversation">❌ Delete</button>
            </>
          )}
        </div>
      </div>

      {/* Mode selector */}
      <div style={{ display: 'flex', gap: '8px', padding: '8px 10px 0', alignItems: 'center' }}>
        <span style={{ fontSize: '13px', color: '#6b7280', fontWeight: 500 }}>Mode:</span>

        {['council', 'hybrid'].map((m) => {
          const isActive = mode === m;
          const isHybrid = m === 'hybrid';
          const activeColor = isHybrid ? '#7c3aed' : '#2563eb';
          return (
            <button
              key={m}
              type="button"
              onClick={() => !isLocked && setMode(m)}
              onMouseEnter={(e) => handleTooltipShow(e, m)}
              onMouseLeave={handleTooltipHide}
              disabled={isLocked}
              title={isLocked ? `Mode locked — this conversation used ${conversationMode} mode` : ''}
              style={{
                padding: '5px 14px',
                borderRadius: '20px',
                border: '1.5px solid',
                borderColor: isActive ? activeColor : '#d1d5db',
                backgroundColor: isActive ? activeColor : 'white',
                color: isActive ? 'white' : '#4b5563',
                fontSize: '12px',
                fontWeight: 600,
                cursor: isLocked ? 'not-allowed' : 'pointer',
                opacity: isLocked && !isActive ? 0.4 : 1,
                transition: 'opacity 0.2s',
              }}
            >
              {isHybrid ? '🔀 Debate' : '🏛️ Council'}
            </button>
          );
        })}

        {isLocked && (
          <span style={{ fontSize: '11px', color: '#9ca3af', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '3px' }}>
            🔒 Mode locked to this conversation
          </span>
        )}
        {!isLocked && mode === 'hybrid' && (
          <span style={{ fontSize: '11px', color: '#7c3aed', fontStyle: 'italic' }}>
            Socratic → Debate → Devil's Advocate → Synthesis
          </span>
        )}
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} className="input-form input-form-top">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />

        <div className="input-with-attach">
          <div className="textarea-row">
            {/* Paperclip button */}
            <button
              type="button"
              className={`file-attach-btn${attachedFile ? ' has-file' : ''}`}
              onClick={handleFileButtonClick}
              disabled={isLoading || isUploading}
              title="Attach a file (pdf, docx, txt, sh, py, md, xls, xlsx)"
            >
              📎
            </button>

            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={attachedFile
                ? `File attached — add a question or just send to get council input on ${attachedFile.name}…`
                : 'Select the mode and submit your question to the Council…'}
              disabled={isLoading}
              rows={3}
            />
          </div>

          {/* File chip / uploading indicator / error */}
          {isUploading && (
            <div className="file-uploading">
              <div className="mini-spinner" />
              Extracting text…
            </div>
          )}
          {!isUploading && attachedFile && (
            <div className="file-chip">
              <span className="chip-icon">📄</span>
              <span className="chip-name" title={attachedFile.name}>{attachedFile.name}</span>
              <button
                type="button"
                className="chip-remove"
                onClick={handleRemoveFile}
                title="Remove file"
              >
                ✕
              </button>
            </div>
          )}
          {uploadError && (
            <div className="upload-error">⚠️ {uploadError}</div>
          )}
        </div>

        <button type="submit" disabled={!canSubmit}>
          {isLoading ? 'Thinking...' : 'Send to Council'}
        </button>
      </form>

      {isLoading && (
        <div className="loading-indicator">
          <div className="loading-spinner"></div>
          <div className="loading-text">{getLoadingMessage()}</div>
        </div>
      )}

      <div className="messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            {message.role === 'user' ? (
              <div className="markdown-content">
                <strong>You:</strong>
                {/* File badge */}
                {parseFileBadge(message.content) && (
                  <div style={{ marginTop: '6px' }}>
                    <span className="file-badge">
                      📄 {parseFileBadge(message.content)}
                    </span>
                  </div>
                )}
                <p>{parseUserText(message.content)}</p>
              </div>
            ) : (
              <div className="assistant-message">
                <ModeBadge msgMode={message.mode} />

                {message.mode === 'hybrid' ? (
                  <HybridView message={message} loadingPhase={hybridLoadingPhase} />
                ) : (
                  <>
                    <div className="stage-container">
                      <Stage1 responses={message.stage1} />
                    </div>
                    <div className="stage-container">
                      <Stage2
                        rankings={message.stage2}
                        labelToModel={message.metadata?.label_to_model}
                        aggregateRankings={message.metadata?.aggregate_rankings}
                      />
                    </div>
                    <div className="stage-container">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <h3 style={{ margin: 0 }}>Stage 3: Final Synthesis</h3>
                        {message.stage3 && (
                          <button
                            onClick={() => handleCopyFinalAnswer(message.stage3.response)}
                            style={{ padding: '6px 12px', backgroundColor: '#4a90e2', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                            title="Copy final answer to clipboard"
                          >
                            📋 Copy Answer
                          </button>
                        )}
                      </div>
                      <Stage3 synthesis={message.stage3} />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}

export default ChatInterface;