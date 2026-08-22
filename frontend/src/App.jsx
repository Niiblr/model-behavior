import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Sidebar from './components/Sidebar';
import PingModal from './components/PingModal';
import './App.css';

const API_BASE = 'http://localhost:8001';

function emptyAssistantMessage(mode) {
  return {
    role: 'assistant',
    mode,
    stage1: [],
    stage2: [],
    stage3: null,
    hybrid_phase1: [],
    hybrid_phase2: [],
    hybrid_phase3: null,
    hybrid_phase4: null,
    participants: [],
    chairman: null,
    rounds: [],
    synthesis: null,
    metadata: { mode },
  };
}

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [showPingModal, setShowPingModal] = useState(false);
  const [streamProgress, setStreamProgress] = useState(null);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/conversations`);
      const data = await response.json();
      setConversations(data);
    } catch (error) {
      console.error('Error loading conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const response = await fetch(`${API_BASE}/api/conversations/${id}`);
      const data = await response.json();
      setCurrentConversation(data);
    } catch (error) {
      console.error('Error loading conversation:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const newConversation = await response.json();
      setCurrentConversationId(newConversation.id);
      setCurrentConversation(newConversation);
      await loadConversations();
    } catch (error) {
      console.error('Error creating conversation:', error);
    }
  };

  const updateLastAssistantMessage = (updater) => {
    setCurrentConversation((prev) => {
      const updatedMessages = [...prev.messages];
      const last = updatedMessages[updatedMessages.length - 1];
      if (last?.role === 'assistant') {
        updatedMessages[updatedMessages.length - 1] = updater({ ...last });
      }
      return { ...prev, messages: updatedMessages };
    });
  };

  // ---- Consensus-mode streaming events ----

  const handleConsensusEvent = (data, assistantMessage, type) => {
    switch (type) {
      case 'consensus_start':
        assistantMessage.participants = data.participants;
        assistantMessage.chairman = data.chairman;
        setStreamProgress({
          mode: 'consensus',
          phase: 'start',
          label: 'The council is convening',
          note: `${data.participants.length} debaters · chairman: ${data.chairman?.name ?? '?'}`,
        });
        break;
      case 'consensus_round_start':
        assistantMessage.rounds = [
          ...assistantMessage.rounds,
          { round: data.round, statements: [], votes: { yes: [], no: [] }, reached: false },
        ];
        setStreamProgress({
          mode: 'consensus',
          phase: 'round',
          round: data.round,
          label: data.round === 0 ? 'Opening statements' : `Debate round ${data.round}`,
          note:
            data.round === 0
              ? 'Every model is drafting its initial position…'
              : 'Members argue, then vote CONSENSUS: YES / NO…',
        });
        break;
      case 'consensus_model_complete': {
        const rounds = [...assistantMessage.rounds];
        const target = rounds.find((r) => r.round === data.round);
        if (target) target.statements = [...target.statements, data.statement];
        assistantMessage.rounds = rounds;
        break;
      }
      case 'consensus_round_complete': {
        const rounds = assistantMessage.rounds.map((r) =>
          r.round === data.round
            ? { ...r, votes: data.votes ?? r.votes, reached: !!data.reached }
            : r
        );
        assistantMessage.rounds = rounds;
        if (!data.reached && data.round > 0) {
          setStreamProgress({
            mode: 'consensus',
            phase: 'round_end',
            round: data.round,
            label: `No majority after round ${data.round}`,
            note: 'The debate continues…',
          });
        }
        break;
      }
      case 'consensus_chairman_review':
        if (assistantMessage.rounds.length > 0) {
          const rounds = [...assistantMessage.rounds];
          rounds[rounds.length - 1] = {
            ...rounds[rounds.length - 1],
            review: data,
          };
          assistantMessage.rounds = rounds;
        }
        setStreamProgress({
          mode: 'consensus',
          phase: 'review',
          label: 'Chairman is verifying alignment',
          note: data.aligned
            ? 'Majority positions look aligned — almost there…'
            : 'Positions conflict — forcing a reconciliation round…',
        });
        break;
      case 'consensus_chairman_start':
        setStreamProgress({
          mode: 'consensus',
          phase: 'chairman',
          label: 'The Chairman has called for order',
          note: 'Delivering the final shared answer…',
        });
        break;
      case 'consensus_synthesis_complete':
        assistantMessage.synthesis = data;
        break;
      default:
        break;
    }
  };

  const handleSendMessage = async (content, mode = 'council', opts = {}) => {
    if (!currentConversationId) return;

    setStreamProgress(
      mode === 'council'
        ? { mode, phase: 'stage1', label: 'Stage 1 — forming initial responses' }
        : mode === 'hybrid'
          ? { mode, phase: 'hybrid_phase1', label: 'Phase 1 — Socratic round' }
          : { mode, phase: 'start', label: 'The council is convening' }
    );

    try {
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, { role: 'user', content }, emptyAssistantMessage(mode)],
      }));

      let assistantMessage = emptyAssistantMessage(mode);

      const endpoint =
        mode === 'hybrid'
          ? `${API_BASE}/api/conversations/${currentConversationId}/message/stream/hybrid`
          : mode === 'consensus'
            ? `${API_BASE}/api/conversations/${currentConversationId}/message/stream/consensus`
            : `${API_BASE}/api/conversations/${currentConversationId}/message/stream`;

      const body =
        mode === 'consensus'
          ? {
              content,
              model_ids: opts.modelIds || [],
              chairman_id: opts.chairmanId,
              max_rounds: 4,
            }
          : { content };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let data;
          try {
            data = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          const type = data.type;

          if (type === 'error') {
            console.error('Stream error:', data.message);
            setStreamProgress(null);
            alert(`Something went wrong during the debate: ${data.message}`);
            return;
          }

          if (
            type.startsWith('consensus_')
          ) {
            handleConsensusEvent(data.data ?? {}, assistantMessage, type);
          } else {
            switch (type) {
              // --- Council mode ---
              case 'stage1_start':
                setStreamProgress({
                  mode: 'council',
                  phase: 'stage1',
                  label: 'Stage 1 — forming initial responses',
                  note: 'Council members are thinking…',
                });
                break;
              case 'stage2_start':
                setStreamProgress({
                  mode: 'council',
                  phase: 'stage2',
                  label: 'Stage 2 — peer rankings',
                  note: "Models are evaluating and ranking each other's responses…",
                });
                break;
              case 'stage3_start':
                setStreamProgress({
                  mode: 'council',
                  phase: 'stage3',
                  label: 'Stage 3 — final synthesis',
                  note: 'The Chairman is delivering the verdict…',
                });
                break;
              // --- Debate (hybrid) mode ---
              case 'hybrid_phase1_start':
                setStreamProgress({
                  mode: 'hybrid',
                  phase: 'hybrid_phase1',
                  label: 'Phase 1 — Socratic',
                  note: 'Models are forming their initial understanding…',
                });
                break;
              case 'hybrid_phase2_start':
                setStreamProgress({
                  mode: 'hybrid',
                  phase: 'hybrid_phase2',
                  label: 'Phase 2 — Debate',
                  note: 'The models are challenging each other…',
                });
                break;
              case 'hybrid_phase3_start':
                setStreamProgress({
                  mode: 'hybrid',
                  phase: 'hybrid_phase3',
                  label: "Phase 3 — Devil's Advocate",
                  note: 'A devil’s advocate has entered the chamber…',
                });
                break;
              case 'hybrid_phase4_start':
                setStreamProgress({
                  mode: 'hybrid',
                  phase: 'hybrid_phase4',
                  label: 'Phase 4 — Final Synthesis',
                  note: 'The Chairman has called for order…',
                });
                break;
              default:
                break;
            }
          }

          // Data-bearing completions update the assistant message
          let changed = false;
          switch (type) {
            case 'stage1_complete':
              assistantMessage.stage1 = data.data;
              changed = true;
              break;
            case 'stage2_complete':
              assistantMessage.stage2 = data.data;
              assistantMessage.metadata = data.metadata;
              changed = true;
              break;
            case 'stage3_complete':
              assistantMessage.stage3 = data.data;
              changed = true;
              break;
            case 'hybrid_phase1_complete':
              assistantMessage.hybrid_phase1 = data.data;
              changed = true;
              break;
            case 'hybrid_phase2_complete':
              assistantMessage.hybrid_phase2 = data.data;
              changed = true;
              break;
            case 'hybrid_phase3_complete':
              assistantMessage.hybrid_phase3 = data.data;
              changed = true;
              break;
            case 'hybrid_phase4_complete':
              assistantMessage.hybrid_phase4 = data.data;
              changed = true;
              break;
            default:
              if (type.startsWith('consensus_')) changed = true;
              break;
          }

          if (changed) {
            const snapshot = { ...assistantMessage };
            updateLastAssistantMessage(() => snapshot);
          }

          if (type === 'title_complete') {
            setCurrentConversation((prev) => ({ ...prev, title: data.data.title }));
            loadConversations();
          }
          if (type === 'complete') {
            setStreamProgress(null);
            loadConversations();
          }
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      alert(`Failed to send message: ${error.message}`);
    } finally {
      setStreamProgress(null);
    }
  };

  const handleUpdateTitle = (newTitle) => {
    setCurrentConversation((prev) => ({ ...prev, title: newTitle }));
    loadConversations();
  };

  const handleDeleteConversation = () => {
    setCurrentConversationId(null);
    setCurrentConversation(null);
    loadConversations();
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentId={currentConversationId}
        onSelect={setCurrentConversationId}
        onNewConversation={createNewConversation}
        onPing={() => setShowPingModal(true)}
      />
      <div className="main">
        {currentConversation ? (
          <ChatInterface
            conversationId={currentConversationId}
            conversationTitle={currentConversation.title}
            messages={currentConversation.messages}
            onSendMessage={handleSendMessage}
            onUpdateTitle={handleUpdateTitle}
            onDelete={handleDeleteConversation}
            streamProgress={streamProgress}
          />
        ) : (
          <div className="welcome">
            <h1>Conclave</h1>
            <p>
              Watch AI models deliberate. Ask a question and let a council of models answer,
              argue, and vote their way to the best response.
            </p>
            <div className="welcome-modes">
              <div className="welcome-mode-card" style={{ borderColor: 'var(--council-border)' }}>
                <div className="welcome-mode-icon">🏛️</div>
                <div className="welcome-mode-name" style={{ color: 'var(--council)' }}>Council</div>
                <div className="welcome-mode-desc">
                  Independent answers, anonymized peer rankings, chairman synthesis.
                </div>
              </div>
              <div className="welcome-mode-card" style={{ borderColor: 'var(--debate-border)' }}>
                <div className="welcome-mode-icon">⚔️</div>
                <div className="welcome-mode-name" style={{ color: 'var(--debate)' }}>Debate</div>
                <div className="welcome-mode-desc">
                  Socratic round, open debate, devil&apos;s advocate, chairman synthesis.
                </div>
              </div>
              <div className="welcome-mode-card" style={{ borderColor: 'var(--consensus-border)' }}>
                <div className="welcome-mode-icon">🤝</div>
                <div className="welcome-mode-name" style={{ color: 'var(--consensus)' }}>Consensus</div>
                <div className="welcome-mode-desc">
                  Any free models debate in rounds until a majority votes for consensus.
                </div>
              </div>
            </div>
            <div className="welcome-footer">
              by Niiblr · based on{' '}
              <a href="https://github.com/karpathy/llm-council" target="_blank" rel="noreferrer">
                karpathy/llm-council
              </a>
            </div>
          </div>
        )}
      </div>
      {showPingModal && <PingModal onClose={() => setShowPingModal(false)} />}
    </div>
  );
}

export default App;
