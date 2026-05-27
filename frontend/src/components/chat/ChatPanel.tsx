'use client';

import { useRef, useEffect, useState } from 'react';
import type { Message } from '../../types/voter';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  language: string;
}

const QUICK_CHIPS = [
  'What is Form 6?',
  'NRI voting rights',
  'Check voter status',
  'Postal ballot',
  'File a grievance',
  'Address proof list',
];

function Dot() {
  return (
    <span style={{
      width: 7, height: 7, borderRadius: '50%',
      background: '#10B981', display: 'inline-block',
      animation: 'pulse 1.8s ease infinite',
    }} />
  );
}

export default function ChatPanel({
  messages, onSendMessage, isLoading, language,
}: ChatPanelProps) {
  const [text, setText] = useState('');
  const feedRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleChip = (q: string) => {
    if (isLoading) return;
    onSendMessage(q);
  };

  return (
    <section style={{
      width: 420, flexShrink: 0,
      display: 'flex', flexDirection: 'column',
      borderRight: '1px solid var(--border)',
      background: 'var(--bg)', overflow: 'hidden',
    }}>

      {/* ── Chat header ── */}
      <div style={{
        padding: '11px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface)',
        display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
          background: 'linear-gradient(135deg, #F97316, #7C2D12)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'Fraunces, serif', fontSize: 16, fontWeight: 700, color: '#fff',
          boxShadow: '0 0 16px var(--saffron-dim)', animation: 'glowRing 3s ease infinite',
        }}>म</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>Voter Assistance</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
            <Dot />
            <span style={{ fontSize: 10.5, color: 'var(--emerald)' }}>Live</span>
            <span style={{ color: 'var(--ink-ghost)' }}>·</span>
            <span style={{ fontSize: 10.5, color: 'var(--ink-ghost)' }}>RAG-grounded · Zero hallucination</span>
          </div>
        </div>
        <div style={{
          fontSize: 10, color: 'var(--ink-ghost)',
          background: 'var(--card)', border: '1px solid var(--border)',
          borderRadius: 6, padding: '4px 8px',
        }}>
          {messages.length} msgs
        </div>
      </div>

      {/* ── Messages feed ── */}
      <div
        ref={feedRef}
        style={{
          flex: 1, overflowY: 'auto',
          padding: '18px 14px 10px',
          display: 'flex', flexDirection: 'column', gap: 16,
        }}
      >
        {messages.length === 0 && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🗳️</div>
              <p className="font-display" style={{ fontSize: 16, color: 'var(--ink)', marginBottom: 6 }}>
                Welcome to Matdaan Mitra
              </p>
              <p style={{ fontSize: 12, color: 'var(--ink-dim)', lineHeight: 1.6 }}>
                Ask me anything about voter registration,<br />
                forms, deadlines, or your polling booth.
              </p>
            </div>
          </div>
        )}

        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} language={language} />
        ))}

        {isLoading && <TypingIndicator />}
      </div>

      {/* ── Composer ── */}
      <div style={{
        padding: '12px 14px',
        borderTop: '1px solid var(--border)',
        background: 'var(--card)', flexShrink: 0,
      }}>
        {/* Quick chips */}
        <div style={{
          display: 'flex', gap: 6, marginBottom: 10,
          overflowX: 'auto', paddingBottom: 2,
        }}>
          {QUICK_CHIPS.map(q => (
            <button
              key={q}
              onClick={() => handleChip(q)}
              disabled={isLoading}
              style={{
                all: 'unset', cursor: isLoading ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
                border: '1px solid var(--border)',
                borderRadius: 20, padding: '4px 11px',
                fontSize: 10.5, color: 'var(--ink-ghost)',
                background: 'transparent', transition: 'all .15s', flexShrink: 0,
                opacity: isLoading ? 0.4 : 1,
              }}
              onMouseEnter={e => {
                if (!isLoading) {
                  e.currentTarget.style.borderColor = 'rgba(249,115,22,0.55)';
                  e.currentTarget.style.color = 'var(--saffron-warm)';
                }
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.color = 'var(--ink-ghost)';
              }}
            >
              {q}
            </button>
          ))}
        </div>

        {/* Input row */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <textarea
            ref={inputRef}
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about forms, deadlines, documents… (Enter to send)"
            disabled={isLoading}
            rows={1}
            style={{
              flex: 1,
              background: 'var(--surface)',
              border: '1px solid var(--border-fine)',
              borderRadius: 13, padding: '11px 14px',
              fontSize: 13, color: 'var(--ink)',
              fontFamily: 'Instrument Sans, sans-serif',
              resize: 'none', minHeight: 44, maxHeight: 120,
              outline: 'none', transition: 'border-color .15s',
              opacity: isLoading ? 0.6 : 1,
            }}
            onFocus={e => (e.currentTarget.style.borderColor = 'rgba(249,115,22,0.5)')}
            onBlur={e => (e.currentTarget.style.borderColor = 'var(--border-fine)')}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !text.trim()}
            style={{
              all: 'unset', cursor: text.trim() && !isLoading ? 'pointer' : 'not-allowed',
              width: 44, height: 44, borderRadius: 12, flexShrink: 0,
              background: text.trim() && !isLoading
                ? 'linear-gradient(135deg, #F97316, #C2410C)'
                : 'var(--card)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 20, color: text.trim() && !isLoading ? '#030508' : 'var(--ink-ghost)',
              transition: 'all .15s',
              boxShadow: text.trim() && !isLoading ? '0 4px 16px var(--saffron-dim)' : 'none',
              fontWeight: 700,
            }}
            onMouseEnter={e => {
              if (text.trim() && !isLoading) {
                e.currentTarget.style.transform = 'scale(1.06)';
                e.currentTarget.style.boxShadow = '0 8px 24px var(--saffron-glow)';
              }
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.boxShadow = text.trim() && !isLoading ? '0 4px 16px var(--saffron-dim)' : 'none';
            }}
          >
            ↑
          </button>
        </div>
      </div>
    </section>
  );
}