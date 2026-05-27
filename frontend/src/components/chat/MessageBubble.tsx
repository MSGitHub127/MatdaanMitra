'use client';

import { useState, useCallback } from 'react';
import type { Message, AgentTraceEntry } from '../../types/voter';
import { formatTime } from '../../lib/utils';
import { synthesizeSpeech } from '../../lib/api';
import ConfidenceRing from './ConfidenceRing';
import SourceDrawer from './SourceDrawer';

interface MessageBubbleProps {
  message: Message;
  language: string;
}

/* ── Bold markdown parser — converts **text** to <strong> ── */
function BoldText({ text }: { text: string }) {
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} style={{ color: 'var(--saffron-warm)', fontWeight: 600 }}>
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

/* ── Agent trace node icons ── */
const TRACE_ICONS: Record<string, string> = {
  intent: '🎯', rag: '🔍', profile: '👤', synthesis: '🧠',
  guardrail: '🛡️', translation: '🌐', live: '📡', live_lookup: '📡',
};

function TraceEntry({ entry }: { entry: AgentTraceEntry }) {
  const isOk = entry.status === 'ok' || entry.status === 'success';
  const color = isOk ? 'var(--emerald)' : 'var(--rose)';
  const icon = TRACE_ICONS[entry.node] ?? '⚙️';

  const detail = entry.decision
    ?? (entry.retrieved_chunks ? `${entry.retrieved_chunks.length} chunks` : null)
    ?? entry.error
    ?? '—';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '5px 8px', borderRadius: 6,
      background: 'var(--card)', border: '1px solid var(--border)',
      marginBottom: 3, fontSize: 11,
    }}>
      <span style={{ fontSize: 13 }}>{icon}</span>
      <span style={{ color: 'var(--ink-dim)', fontWeight: 500, minWidth: 72 }}>{entry.node}</span>
      <span style={{ color, flex: 1 }}>{detail}</span>
      {entry.latency_ms != null && (
        <span className="font-mono" style={{ color: 'var(--ink-ghost)', fontSize: 10 }}>
          {entry.latency_ms}ms
        </span>
      )}
      <span style={{ color, fontSize: 9, letterSpacing: '0.06em', fontWeight: 700 }}>
        {(entry.status ?? 'ok').toUpperCase()}
      </span>
    </div>
  );
}

export default function MessageBubble({ message, language }: MessageBubbleProps) {
  const isBot = message.role === 'bot';
  const [srcOpen, setSrcOpen] = useState(false);
  const [traceOpen, setTraceOpen] = useState(false);
  const [ttsLoading, setTtsLoading] = useState(false);
  const [ttsActive, setTtsActive] = useState(false);

  const handleTTS = useCallback(async () => {
    if (ttsLoading) return;
    setTtsLoading(true);
    try {
      const b64 = await synthesizeSpeech(message.text, language);
      if (b64) {
        const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
        const blob = new Blob([bytes], { type: 'audio/wav' });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        setTtsActive(true);
        audio.onended = () => {
          setTtsActive(false);
          URL.revokeObjectURL(url);
        };
        audio.play();
      }
    } finally {
      setTtsLoading(false);
    }
  }, [message.text, language, ttsLoading]);

  return (
    <div
      className="fade-up"
      style={{
        display: 'flex',
        flexDirection: isBot ? 'row' : 'row-reverse',
        gap: 9, alignItems: 'flex-end',
      }}
    >
      {/* Avatar */}
      {isBot ? (
        <div style={{
          width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
          background: 'linear-gradient(135deg, #F97316, #7C2D12)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'Fraunces, serif', fontSize: 11, fontWeight: 700, color: '#fff',
          boxShadow: '0 0 10px var(--saffron-dim)',
        }}>म</div>
      ) : (
        <div style={{
          width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
          background: 'linear-gradient(135deg, #38BDF8, #0369A1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, fontWeight: 700, color: '#fff',
        }}>U</div>
      )}

      <div style={{
        maxWidth: '83%', display: 'flex', flexDirection: 'column', gap: 5,
        alignItems: isBot ? 'flex-start' : 'flex-end',
      }}>
        {/* Bubble */}
        <div style={{
          background: isBot
            ? 'var(--card)'
            : 'linear-gradient(135deg, rgba(56,189,248,0.15), rgba(56,189,248,0.07))',
          border: `1px solid ${isBot ? 'var(--border)' : 'rgba(56,189,248,0.4)'}`,
          borderRadius: isBot ? '4px 14px 14px 14px' : '14px 4px 14px 14px',
          padding: '11px 14px',
          fontSize: 13.5, lineHeight: 1.72,
          color: 'var(--ink)',
          whiteSpace: 'pre-line',
        }}>
          {isBot ? <BoldText text={message.text} /> : message.text}

          {/* Streaming cursor */}
          {message.isStreaming && (
            <span style={{
              display: 'inline-block', width: 2, height: 14,
              background: 'var(--saffron)', marginLeft: 3,
              animation: 'pulse 1s ease infinite', verticalAlign: 'middle',
            }} />
          )}
        </div>

        {/* Bot meta row */}
        {isBot && !message.isStreaming && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingLeft: 2 }}>
            {message.confidence != null && (
              <ConfidenceRing score={message.confidence} size={28} />
            )}

            {/* Source toggle */}
            {message.sourceChunks && message.sourceChunks.length > 0 && (
              <button onClick={() => setSrcOpen(v => !v)} style={{
                all: 'unset', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 4,
                fontSize: 10.5, color: 'var(--ink-ghost)', transition: 'color .15s',
              }}
                onMouseEnter={e => (e.currentTarget.style.color = 'var(--sapphire)')}
                onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-ghost)')}
              >
                <span style={{
                  width: 16, height: 16, borderRadius: '50%',
                  background: 'var(--sapphire-dim)', border: '1px solid rgba(56,189,248,0.44)',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 9, color: 'var(--sapphire)', fontWeight: 700,
                }}>i</span>
                Source {srcOpen ? '▲' : '▼'}
              </button>
            )}

            {/* Trace toggle */}
            {message.agentTrace && message.agentTrace.length > 0 && (
              <button onClick={() => setTraceOpen(v => !v)} style={{
                all: 'unset', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 4,
                fontSize: 10.5, color: 'var(--ink-ghost)', transition: 'color .15s',
              }}
                onMouseEnter={e => (e.currentTarget.style.color = 'var(--violet)')}
                onMouseLeave={e => (e.currentTarget.style.color = 'var(--ink-ghost)')}
              >
                <span style={{
                  width: 16, height: 16, borderRadius: '50%',
                  background: 'var(--violet-dim)', border: '1px solid rgba(167,139,250,0.44)',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 9, color: 'var(--violet)', fontWeight: 700,
                }}>⚙</span>
                Trace {traceOpen ? '▲' : '▼'}
              </button>
            )}

            {/* TTS button */}
            <button
              onClick={handleTTS}
              disabled={ttsLoading}
              title="Listen (Sarvam AI TTS)"
              style={{
                all: 'unset', cursor: 'pointer',
                width: 24, height: 24, borderRadius: 6,
                background: 'var(--card)', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, transition: 'all .15s',
                color: ttsActive ? 'var(--saffron)' : 'var(--ink-ghost)',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--saffron-dim)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--card)')}
            >
              {ttsLoading ? '⏳' : ttsActive ? '🔊' : '🔈'}
            </button>
          </div>
        )}

        {/* Source drawer */}
        {srcOpen && message.sourceChunks && message.sourceChunks.length > 0 && (
          <div className="fade-in" style={{
            background: 'var(--sapphire-dim)',
            border: '1px solid rgba(56,189,248,0.3)',
            borderRadius: 10, padding: '10px 13px',
            fontSize: 11, maxWidth: '100%',
          }}>
            <SourceDrawer chunks={message.sourceChunks} />
          </div>
        )}

        {/* Agent trace drawer */}
        {traceOpen && message.agentTrace && message.agentTrace.length > 0 && (
          <div className="fade-in" style={{
            background: 'var(--card)',
            border: '1px solid rgba(167,139,250,0.28)',
            borderRadius: 10, padding: '10px 11px',
            maxWidth: '100%', minWidth: 260,
          }}>
            <div style={{ fontSize: 10, color: 'var(--violet)', letterSpacing: '.08em', fontWeight: 700, marginBottom: 7 }}>
              AGENT DECISION TRACE
            </div>
            {message.agentTrace.map((entry, i) => (
              <TraceEntry key={i} entry={entry as AgentTraceEntry} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div style={{ fontSize: 9.5, color: 'var(--ink-ghost)' }}>
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}