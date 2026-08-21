import React, { useState, useRef, useEffect } from 'react';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import HybridView from './HybridView';
import ConsensusView from './ConsensusView';
import ModelPicker from './ModelPicker';
import Header from './Header';
import './ChatInterface.css';

const ACCEPTED_TYPES = '.pdf,.docx,.txt,.sh,.py,.md,.xls,.xlsx';
const API_BASE = 'http://localhost:8001';

const MODES = {
  council: {
    key: 'council',
    label: 'Council',
    icon: '🏛️',
    sendLabel: 'Convene Council',
    tooltip:
      '🏛️ Council Mode\n\nA structured 3-stage process:\n• Stage 1: Each AI model independently forms its own answer\n• Stage 2: Models evaluate and rank each other\'s responses\n• Stage 3: A Chairman AI synthesizes the best final answer',
  },
  hybrid: {
    key: 'hybrid',
    label: 'Debate',
    icon: '⚔️',
    sendLabel: 'Begin Debate',
    tooltip:
      "⚔️ Debate Mode\n\nA dynamic 4-phase process:\n• Phase 1: Models form initial understanding (Socratic)\n• Phase 2: Models debate and challenge each other\n• Phase 3: A Devil's Advocate challenges the consensus\n• Phase 4: A Chairman delivers the final synthesis",
  },
  consensus: {
    key: 'consensus',
    label: 'Consensus',
    icon: '🤝',
    sendLabel: 'Call the Vote',
    tooltip:
      '🤝 Consensus Mode\n\nFree models debate in rounds until a majority agrees:\n• Pick any roster of free OpenRouter models\n• Each round ends with a CONSENSUS vote\n• Majority wins; the Chairman verifies alignment\n• The Chairman then delivers the final shared answer',
  },
};

function ProgressRail({ progress }) {
  if (!progress) return null;

  let steps = null;
  let activeIdx = -1;

  if (progress.mode === 'council') {
    steps = ['Responses', 'Rankings', 'Synthesis'];
    activeIdx = { stage1: 0, stage2: 1, stage3: 2 }[progress.phase] ?? -1;
  } else if (progress.mode === 'hybrid') {
    steps = ['Socratic', 'Debate', "Devil's Advocate", 'Synthesis'];
    const n = Number((progress.phase || '').replace('hybrid_phase', ''));
    activeIdx = n >= 1 && n <= 4 ? n - 1 : -1;
  }

  return (
    <div className={`progress-rail ${progress.mode}`} role="status">
      <div className="pr-spinner" />
      <div className="pr-body">
        <div className="pr-label">{progress.label}</div>
        {progress.note && <div className="pr-note">{progress.note}</div>}
        {steps && (
          <div className="pr-steps">
            {steps.map((s, i) => (
              <React.Fragment key={s}>
                {i > 0 && <span className="pr-step-sep" />}
                <span className={`pr-step ${i < activeIdx ? 'done' : ''} ${i === activeIdx ? 'active' : ''}`}>
                  {i < activeIdx ? '✓ ' : ''}
                  {s}
                </span>
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ChatInterface({
  conversationId,
  conversationTitle,
  messages,
  onSendMessage,
  onUpdateTitle,
  onDelete,
  streamProgress,
}) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('council');

  // Consensus roster state
  const [selectedModelIds, setSelectedModelIds] = useState([]);
  const [chairmanId, setChairmanId] = useState(null);

  // File upload state
  const [attachedFile, setAttachedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const [tooltip, setTooltip] = useState({ visible: false, text: '', x: 0, y: 0 });

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const messagesContainerRef = useRef(null);

  const isLoading = !!streamProgress;

  const conversationMode = (() => {
    const firstAssistant = messages.find((m) => m.role === 'assistant');
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
      text: MODES[modeKey].tooltip,
      x: rect.left + rect.width / 2,
      y: rect.top + window.scrollY - 8,
    });
  };

  const handleTooltipHide = () => {
    setTooltip({ ...tooltip, visible: false });
  };

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const isNearBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight < 140;
    if (isNearBottom || messages.length === 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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

  const consensusReady =
    mode !== 'consensus' || (selectedModelIds.length >= 3 && !!chairmanId);
  const canSubmit = (input.trim() || attachedFile) && !isLoading && !isUploading && consensusReady;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;

    const finalContent = buildMessageWithFile(input, attachedFile);
    const fileNameForDisplay = attachedFile ? attachedFile.name : null;

    const opts =
      mode === 'consensus'
        ? { modelIds: selectedModelIds, chairmanId }
        : undefined;

    setAttachedFile(null);
    setUploadError('');

    await onSendMessage(finalContent, mode, opts, fileNameForDisplay);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleClearMessages = async () => {
    if (!window.confirm('Are you sure you want to clear all messages? This cannot be undone.')) return;
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`, {
        method: 'DELETE',
      });
      if (response.ok) window.location.reload();
    } catch (error) {
      console.error('Error clearing messages:', error);
    }
  };

  const handleRename = async (newTitle) => {
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/title`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle }),
      });
      if (response.ok) onUpdateTitle(newTitle);
    } catch (error) {
      console.error('Error renaming conversation:', error);
    }
  };

  const handleDeleteConversation = async () => {
    if (!window.confirm('Are you sure you want to delete this entire conversation? This cannot be undone.'))
      return;
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
        method: 'DELETE',
      });
      if (response.ok) onDelete();
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const handleExport = async (format = 'markdown') => {
    try {
      const url =
        format === 'html'
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
    }
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
    const questionMatch = content.match(/\nUser question: ([\s\S]*)$/);
    if (questionMatch) return questionMatch[1];
    return content;
  };

  // Derive view-specific live indicators from streamProgress
  const liveConsensusRound =
    streamProgress?.mode === 'consensus' &&
    streamProgress?.phase === 'round'
      ? streamProgress.round
      : null;
  const hybridLoadingPhase =
    streamProgress?.mode === 'hybrid' ? streamProgress.phase || '' : '';

  const activeMode = MODES[mode];

  return (
    <div className="chat-interface">
      {tooltip.visible && (
        <div
          className="mode-tooltip"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
          <div className="mode-tooltip-arrow" />
        </div>
      )}

      <Header
        title={conversationTitle}
        hasMessages={messages.length > 0}
        onRename={handleRename}
        onExportMarkdown={() => handleExport('markdown')}
        onExportHtml={() => handleExport('html')}
        onClear={handleClearMessages}
        onDelete={handleDeleteConversation}
      />

      <div className="messages" ref={messagesContainerRef}>
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            {message.role === 'user' ? (
              <div className="user-bubble markdown-content">
                {parseFileBadge(message.content) && (
                  <span className="file-badge">📄 {parseFileBadge(message.content)}</span>
                )}
                <p>{parseUserText(message.content)}</p>
              </div>
            ) : (
              <div className="assistant-message">
                {message.mode === 'consensus' ? (
                  <ConsensusView message={message} liveRound={liveConsensusRound} />
                ) : message.mode === 'hybrid' ? (
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
                      <div className="stage-heading-row">
                        <h3>Stage 3: Final Synthesis</h3>
                        {message.stage3?.response && (
                          <button
                            className="copy-answer-btn"
                            onClick={() =>
                              navigator.clipboard.writeText(message.stage3.response)
                            }
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

      <form className="composer" data-mode={mode} onSubmit={handleSubmit}>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />

        {/* Segmented mode selector */}
        <div className="composer-modes">
          <span className="composer-modes-label">Mode</span>
          <div className="segmented" role="tablist">
            {Object.values(MODES).map((m) => (
              <button
                key={m.key}
                type="button"
                role="tab"
                aria-selected={mode === m.key}
                className={`segment ${mode === m.key ? 'active' : ''}`}
                onClick={() => !isLocked && setMode(m.key)}
                onMouseEnter={(e) => handleTooltipShow(e, m.key)}
                onMouseLeave={handleTooltipHide}
                disabled={isLocked}
                title={
                  isLocked ? `Mode locked — this conversation used ${conversationMode} mode` : ''
                }
              >
                <span className="segment-icon">{m.icon}</span>
                {m.label}
              </button>
            ))}
          </div>
          {isLocked ? (
            <span className="mode-lock-hint">🔒 locked</span>
          ) : (
            <span className="mode-hint">{activeMode.tooltip.split('\n')[1]}</span>
          )}
        </div>

        {/* Model picker for consensus mode */}
        {mode === 'consensus' && (
          <ModelPicker
            selectedIds={selectedModelIds}
            onChange={(ids) => {
              setSelectedModelIds(ids);
              if (chairmanId && !ids.includes(chairmanId)) setChairmanId(null);
            }}
            chairmanId={chairmanId}
            onChairmanChange={setChairmanId}
            disabled={isLoading}
            defaultCollapsed={isLocked && selectedModelIds.length === 0}
          />
        )}

        <div className="textarea-row">
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
            placeholder={
              attachedFile
                ? `File attached — add a question or just send…`
                : `Ask the council anything…`
            }
            disabled={isLoading}
            rows={3}
          />

          <button type="submit" className="send-btn" disabled={!canSubmit}>
            {isLoading ? 'Working…' : `${activeMode.icon} ${activeMode.sendLabel}`}
          </button>
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
            <span className="chip-name" title={attachedFile.name}>
              {attachedFile.name}
            </span>
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
        {uploadError && <div className="upload-error">⚠️ {uploadError}</div>}
      </form>

      {streamProgress && <ProgressRail progress={streamProgress} />}
    </div>
  );
}

export default ChatInterface;
