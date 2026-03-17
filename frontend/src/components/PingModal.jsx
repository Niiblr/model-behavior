import { useState } from 'react';
import './PingModal.css';

export default function PingModal({ onClose }) {
    const [results, setResults] = useState([]);
    const [isPinging, setIsPinging] = useState(false);
    const [pendingModels, setPendingModels] = useState([]);
    const [done, setDone] = useState(false);

    const startPing = async () => {
        setIsPinging(true);
        setResults([]);
        setDone(false);

        try {
            const response = await fetch('http://localhost:8001/api/ping');
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done: streamDone, value } = await reader.read();
                if (streamDone) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const event = JSON.parse(line.slice(6));

                            if (event.type === 'ping_start') {
                                setPendingModels(event.models);
                            } else if (event.type === 'ping_result') {
                                setResults(prev => [...prev, event.data]);
                                setPendingModels(prev => prev.filter(m => m !== event.data.model));
                            } else if (event.type === 'ping_complete') {
                                setDone(true);
                                setIsPinging(false);
                            }
                        } catch (e) {
                            console.error('Failed to parse ping event:', e);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Ping failed:', error);
            setIsPinging(false);
            setDone(true);
        }
    };

    const sortedResults = [...results].sort((a, b) => {
        if (a.status === 'ok' && b.status !== 'ok') return -1;
        if (a.status !== 'ok' && b.status === 'ok') return 1;
        return a.latency_ms - b.latency_ms;
    });

    const okCount = results.filter(r => r.status === 'ok').length;
    const errorCount = results.filter(r => r.status === 'error').length;

    return (
        <div className="ping-overlay" onClick={onClose}>
            <div className="ping-modal" onClick={e => e.stopPropagation()}>
                <div className="ping-header">
                    <h2>📡 Model Connectivity Test</h2>
                    <button className="ping-close-btn" onClick={onClose}>✕</button>
                </div>

                {!isPinging && !done && (
                    <div className="ping-start-area">
                        <p>Send a minimal "pong" test to all configured models to check connectivity and measure response times.</p>
                        <button className="ping-run-btn" onClick={startPing}>
                            Run Test
                        </button>
                    </div>
                )}

                {(isPinging || done) && (
                    <div className="ping-results">
                        {done && (
                            <div className="ping-summary">
                                <span className="ping-summary-ok">✅ {okCount} online</span>
                                {errorCount > 0 && <span className="ping-summary-err">❌ {errorCount} failed</span>}
                            </div>
                        )}

                        {sortedResults.map((r, i) => (
                            <div key={i} className={`ping-row ${r.status === 'ok' ? 'ping-row-ok' : 'ping-row-err'}`}>
                                <span className="ping-status-icon">{r.status === 'ok' ? '✅' : '❌'}</span>
                                <span className="ping-model-name">{r.model}</span>
                                <span className="ping-latency">{r.latency_ms}ms</span>
                            </div>
                        ))}

                        {pendingModels.map((name, i) => (
                            <div key={`pending-${i}`} className="ping-row ping-row-pending">
                                <span className="ping-status-icon ping-spinner">⏳</span>
                                <span className="ping-model-name">{name}</span>
                                <span className="ping-latency">…</span>
                            </div>
                        ))}

                        {done && (
                            <button className="ping-run-btn ping-rerun-btn" onClick={startPing}>
                                Run Again
                            </button>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
