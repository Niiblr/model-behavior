import React, { useState, useEffect, useMemo } from 'react';
import './ModelPicker.css';

const API_BASE = 'http://localhost:8001';
const MIN_MODELS = 3;
const MAX_MODELS = 8;

// Cache the catalog across mounts so it isn't refetched on every open
let catalogCache = null;

function formatContext(ctx) {
  if (!ctx) return null;
  if (ctx >= 1_000_000) return `${(ctx / 1_000_000).toFixed(ctx % 1_000_000 === 0 ? 0 : 1)}M ctx`;
  if (ctx >= 1000) return `${Math.round(ctx / 1000)}K ctx`;
  return `${ctx} ctx`;
}

function ModelPicker({ selectedIds, onChange, chairmanId, onChairmanChange, disabled, defaultCollapsed = false }) {
  const [models, setModels] = useState(catalogCache);
  const [loading, setLoading] = useState(!catalogCache);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(`${API_BASE}/api/models/free`);
        const data = await response.json();
        if (cancelled) return;

        if (data.requires_key) {
          setError(data.error);
        } else if (data.error) {
          setError(data.error);
        } else {
          catalogCache = data.models;
          setModels(data.models);
        }
      } catch {
        if (!cancelled) setError('Could not reach the backend to fetch free models.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    if (!catalogCache) load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!models) return [];
    const q = search.trim().toLowerCase();
    if (!q) return models;
    return models.filter(
      (m) => m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q)
    );
  }, [models, search]);

  const toggleModel = (id) => {
    if (disabled) return;
    let next;
    if (selectedIds.includes(id)) {
      next = selectedIds.filter((x) => x !== id);
    } else {
      if (selectedIds.length >= MAX_MODELS) return;
      next = [...selectedIds, id];
    }
    onChange(next);
    // Chairman must stay valid
    if (chairmanId && !next.includes(chairmanId)) {
      onChairmanChange(null);
    }
  };

  const selectedModels = (models || []).filter((m) => selectedIds.includes(m.id));
  const canStart = selectedIds.length >= MIN_MODELS && !!chairmanId;

  return (
    <div className={`model-picker ${disabled ? 'disabled' : ''}`}>
      <button
        type="button"
        className="mp-collapse"
        onClick={() => setCollapsed(!collapsed)}
        title={collapsed ? 'Show model roster' : 'Hide model roster'}
      >
        <span className="mp-collapse-label">
          🤝 Debate roster — <strong>{selectedIds.length}</strong> selected
          {chairmanId && selectedModels.length > 0
            ? ` · chair: ${selectedModels.find((m) => m.id === chairmanId)?.name ?? ''}`
            : ''}
        </span>
        <span className="mp-collapse-chevron">{collapsed ? '▾' : '▴'}</span>
      </button>

      {collapsed ? null : loading ? (
        <div className="mp-loading">
          <div className="mp-spinner" />
          Fetching the free model roster from models.dev…
        </div>
      ) : error ? (
        <div className="mp-error">⚠️ {error}</div>
      ) : (
        <>
          <div className="mp-toolbar">
            <span className="mp-count">
              <strong>{selectedIds.length}</strong> / {MAX_MODELS} selected
              <span className={`mp-count-hint ${canStart ? '' : 'warn'}`}>
                {selectedIds.length < MIN_MODELS
                  ? ` · pick at least ${MIN_MODELS}`
                  : chairmanId
                    ? ''
                    : ' · choose a chairman'}
              </span>
            </span>
            <input
              type="search"
              className="mp-search"
              placeholder="Search free models…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="mp-list">
            {filtered.length === 0 && (
              <div className="mp-empty">No models match “{search}”.</div>
            )}
            {filtered.map((m) => {
              const checked = selectedIds.includes(m.id);
              const isChairman = chairmanId === m.id;
              const ctx = formatContext(m.context_length);
              return (
                <label
                  key={m.id}
                  className={`mp-item ${checked ? 'checked' : ''} ${isChairman ? 'chairman' : ''}`}
                  title={m.description || m.id}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={disabled || (!checked && selectedIds.length >= MAX_MODELS)}
                    onChange={() => toggleModel(m.id)}
                  />
                  <div className="mp-item-text">
                    <span className="mp-item-name">{m.name}</span>
                    <span className="mp-item-id">{m.id}</span>
                  </div>
                  {isChairman && <span className="mp-chairman-badge">⚖️ Chair</span>}
                  {ctx && <span className="mp-ctx">{ctx}</span>}
                </label>
              );
            })}
          </div>

          {selectedIds.length >= MIN_MODELS && (
            <div className="mp-chairman-row">
              <span className="mp-chairman-label">Chairman (debates &amp; abstains from voting):</span>
              <select
                value={chairmanId || ''}
                onChange={(e) => onChairmanChange(e.target.value || null)}
                disabled={disabled}
              >
                <option value="">Select chairman…</option>
                {selectedModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ModelPicker;
