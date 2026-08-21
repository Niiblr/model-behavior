import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './ConsensusView.css';

function VoteBadge({ verdict }) {
  if (verdict === 'YES') return <span className="cv-vote yes">✓ consensus</span>;
  if (verdict === 'NO') return <span className="cv-vote no">• not yet</span>;
  return null;
}

function StatementCard({ statement }) {
  return (
    <div className={`cv-statement ${statement.failed ? 'failed' : ''}`}>
      <div className="cv-statement-head">
        <div className="cv-avatar">{statement.model.charAt(0)}</div>
        <span className="cv-statement-model">{statement.model}</span>
        <VoteBadge verdict={statement.verdict} />
        {statement.failed && <span className="cv-vote failed">failed to respond</span>}
      </div>
      {!statement.failed && (
        <>
          <div className="cv-statement-body markdown-content">
            <ReactMarkdown>{statement.response}</ReactMarkdown>
          </div>
          {statement.position && (
            <div className="cv-position">
              <span className="cv-position-label">Final position</span>
              <ReactMarkdown>{statement.position}</ReactMarkdown>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SkeletonStatement({ name }) {
  return (
    <div className="cv-statement cv-skeleton">
      <div className="cv-statement-head">
        <div className="cv-avatar">{name ? name.charAt(0) : '?'}</div>
        <span className="cv-statement-model">{name || '…'}</span>
      </div>
      <div className="cv-skeleton-lines">
        <div className="cv-skeleton-line" style={{ width: '92%' }} />
        <div className="cv-skeleton-line" style={{ width: '78%' }} />
        <div className="cv-skeleton-line" style={{ width: '85%' }} />
      </div>
    </div>
  );
}

function TallyBar({ votes }) {
  const yes = (votes?.yes || []).length;
  const no = (votes?.no || []).length;
  const total = yes + no;
  if (total === 0) return null;

  const yesPct = total > 0 ? Math.round((yes / total) * 100) : 0;
  return (
    <div className="cv-tally">
      <div className="cv-tally-bar">
        <div className="cv-tally-yes" style={{ width: `${yesPct}%` }} />
        <div className="cv-tally-no" style={{ width: `${100 - yesPct}%` }} />
      </div>
      <div className="cv-tally-labels">
        <span className="cv-tally-yes-label">YES {yes}</span>
        <span className="cv-tally-no-label">NO {no}</span>
        {yes * 2 > total && <span className="cv-tally-majority">majority ✓</span>}
      </div>
    </div>
  );
}

function RoundBlock({ roundEntry, participants, isLiveRound }) {
  const [isOpen, setIsOpen] = useState(true);
  const roundNum = roundEntry.round;
  const label =
    roundNum === 0
      ? 'Opening Statements'
      : `Round ${roundNum}`;

  const statements = roundEntry.statements || [];
  const roster = participants || [];

  // Which participants still owe a statement this round?
  const responded = new Set(statements.map((s) => s.model));
  const pending = roster.filter((p) => !responded.has(p.name));

  return (
    <div className={`cv-round ${isLiveRound ? 'live' : ''} ${roundEntry.reached ? 'reached' : ''}`}>
      <button className="cv-round-header" onClick={() => setIsOpen(!isOpen)}>
        <span className="cv-round-title">
          {label}
          {roundEntry.reached && <span className="cv-reached-badge">majority reached</span>}
        </span>
        {isLiveRound && (
          <span className="cv-live-indicator">
            <span className="cv-live-dot" /> in progress
          </span>
        )}
        <span className="cv-round-toggle">{isOpen ? '▾' : '▸'}</span>
      </button>

      {isOpen && (
        <div className="cv-round-body">
          {roundEntry.review && (
            <div className={`cv-review ${roundEntry.review.aligned ? 'aligned' : 'conflicted'}`}>
              <strong>⚖️ Chairman review: {roundEntry.review.aligned ? 'ALIGNED' : 'CONFLICTED'}</strong>
              {' — '}
              {roundEntry.review.reasoning}
            </div>
          )}

          {statements.map((stmt, i) => (
            <StatementCard key={`${stmt.model}-${i}`} statement={stmt} />
          ))}

          {(isLiveRound || pending.length > 0) &&
            pending.map((p) => <SkeletonStatement key={p.id} name={p.name} />)}

          {!isLiveRound && <TallyBar votes={roundEntry.votes} />}
        </div>
      )}
    </div>
  );
}

function ConsensusView({ message, liveRound }) {
  const participants = message.participants || [];
  const chairman = message.chairman;
  const rounds = message.rounds || [];
  const synthesis = message.synthesis;
  const lastRoundNum = rounds.length > 0 ? rounds[rounds.length - 1].round : -1;

  return (
    <div className="consensus-view">
      <div className="cv-header">
        <span className="cv-badge">🤝 Consensus Mode</span>
        <span className="cv-header-sub">
          {participants.length} debaters ·{' '}
          {chairman ? `chairman: ${chairman.name}` : 'no chairman'} · majority vote ends the debate
        </span>
      </div>

      {rounds.map((roundEntry) => (
        <RoundBlock
          key={roundEntry.round}
          roundEntry={roundEntry}
          participants={participants}
          isLiveRound={liveRound === roundEntry.round}
        />
      ))}

      {/* Awaiting synthesis after final round closed */}
      {!synthesis && lastRoundNum >= 0 && liveRound == null && (
        <div className="cv-synthesis cv-synthesis-pending">
          <div className="cv-spinner" />
          The Chairman is preparing the council&apos;s final answer…
        </div>
      )}

      {synthesis && (
        <div className="cv-synthesis">
          <div className="cv-synthesis-head">
            <span>✨ Council Consensus</span>
            <span className="cv-synthesis-model">{synthesis.model}</span>
          </div>
          <div className="markdown-content">
            <ReactMarkdown>{synthesis.response}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

export default ConsensusView;
