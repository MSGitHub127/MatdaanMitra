'use client';

import { useState } from 'react';
import type { VoterProfile } from '../../types/voter';

const LANGUAGES = [
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'hi', label: 'हि', name: 'Hindi' },
  { code: 'mr', label: 'मर', name: 'Marathi' },
  { code: 'ta', label: 'தமி', name: 'Tamil' },
  { code: 'te', label: 'తె', name: 'Telugu' },
  { code: 'bn', label: 'বাং', name: 'Bengali' },
  { code: 'kn', label: 'ಕನ', name: 'Kannada' },
  { code: 'gu', label: 'ગુ', name: 'Gujarati' },
  { code: 'pa', label: 'ਪੰ', name: 'Punjabi' },
];

interface HeaderProps {
  profile: VoterProfile;
  language: string;
  onLanguageChange: (lang: string) => void;
}

/* ── Tricolor logo circle ── */
function Logo({ size = 36 }: { size?: number }) {
  return (
    <div
      style={{
        width: size, height: size, borderRadius: '50%',
        position: 'relative', overflow: 'hidden', flexShrink: 0,
        boxShadow: '0 0 0 1.5px rgba(249,115,22,0.4), 0 0 18px rgba(249,115,22,0.15)',
      }}
    >
      <div style={{
        position: 'absolute', inset: 0,
        background: 'conic-gradient(#FF9933 0deg 120deg, #F0EDE6 120deg 240deg, #138808 240deg 360deg)',
      }} />
      <div style={{
        position: 'absolute', top: '50%', left: '50%',
        transform: 'translate(-50%,-50%)',
        width: size * 0.38, height: size * 0.38,
        borderRadius: '50%', background: '#00008B',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{ width: size * 0.09, height: size * 0.09, borderRadius: '50%', background: 'rgba(255,255,255,0.9)' }} />
      </div>
    </div>
  );
}

/* ── Status dot ── */
function Dot({ pulse = false }: { pulse?: boolean }) {
  return (
    <span style={{
      width: 7, height: 7, borderRadius: '50%',
      background: '#10B981', display: 'inline-block', flexShrink: 0,
      ...(pulse ? { animation: 'pulse 1.8s ease infinite' } : {}),
    }} />
  );
}

export default function Header({ profile, language, onLanguageChange }: HeaderProps) {
  const [langOpen, setLangOpen] = useState(false);
  const currentLang = LANGUAGES.find(l => l.code === language) ?? LANGUAGES[0];

  const initials = profile.name
    ? profile.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'MM';

  const regTypeLabel = profile.registration_type
    ? profile.registration_type.toUpperCase().replace('_', '-')
    : 'VOTER';

  return (
    <header style={{
      height: 58, flexShrink: 0, position: 'relative', zIndex: 20,
      background: 'var(--surface)',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center',
      padding: '0 20px', gap: 14,
    }}>

      {/* ── Logo + wordmark ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 11, flexShrink: 0 }}>
        <Logo size={36} />
        <div>
          <div
            className="shimmer-fire font-display"
            style={{ fontSize: 18, lineHeight: 1, letterSpacing: '-0.02em', fontWeight: 700 }}
          >
            मतदान मित्र
          </div>
          <div style={{ fontSize: 8.5, color: 'var(--ink-ghost)', letterSpacing: '.18em', marginTop: 2 }}>
            MATDAAN MITRA · ECI VERIFIED
          </div>
        </div>
      </div>

      {/* ── Status ribbon (centre) ── */}
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
        <div style={{
          background: 'var(--saffron-trace)',
          border: '1px solid rgba(249,115,22,0.22)',
          borderRadius: 20, padding: '5px 18px',
          display: 'flex', alignItems: 'center', gap: 10,
          fontSize: 11.5, color: 'var(--saffron-warm)',
        }}>
          <Dot pulse />
          <span>RAG Pipeline Active</span>
          <span style={{ color: 'var(--ink-ghost)' }}>·</span>
          <span>ECI Corpus · Synced Apr 2026</span>
          <span style={{ color: 'var(--ink-ghost)' }}>·</span>
          <span style={{ color: 'var(--saffron)', fontWeight: 600 }}>Gemini 1.5 Pro</span>
        </div>
      </div>

      {/* ── Right controls ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>

        {/* Language dropdown */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setLangOpen(v => !v)}
            style={{
              all: 'unset', cursor: 'pointer',
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: 9, padding: '5px 13px',
              display: 'flex', alignItems: 'center', gap: 7,
              fontSize: 12, color: 'var(--ink-dim)', transition: 'all .15s',
            }}
          >
            🌐 <span style={{ fontWeight: 600 }}>{currentLang.label}</span>
            <span style={{ fontSize: 9, color: 'var(--ink-ghost)' }}>▾</span>
          </button>

          {langOpen && (
            <div
              className="glass slide-dn"
              style={{
                position: 'absolute', top: 'calc(100% + 6px)', right: 0,
                border: '1px solid var(--border)',
                borderRadius: 12, padding: 6, zIndex: 200, width: 130,
              }}
            >
              {LANGUAGES.map(l => (
                <button
                  key={l.code}
                  onClick={() => { onLanguageChange(l.code); setLangOpen(false); }}
                  style={{
                    all: 'unset', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 8,
                    width: '100%', padding: '6px 10px', borderRadius: 7,
                    transition: 'background .12s',
                    color: language === l.code ? 'var(--saffron)' : 'var(--ink-dim)',
                    fontWeight: language === l.code ? 600 : 400,
                    fontSize: 12,
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--card)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <span style={{ fontSize: 14 }}>{l.label}</span>
                  <span style={{ fontSize: 10.5 }}>{l.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Voter identity pill */}
        <div style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 20, padding: '5px 13px',
          display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5,
        }}>
          <div style={{
            width: 24, height: 24, borderRadius: '50%',
            background: 'linear-gradient(135deg, #F97316, #B45309)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 9, fontWeight: 700, color: '#fff', flexShrink: 0,
            boxShadow: '0 0 10px rgba(249,115,22,0.3)',
          }}>
            {initials}
          </div>
          <span style={{ color: 'var(--ink-dim)' }}>
            {profile.name?.split(' ')[0] ?? 'Voter'}
          </span>
          <span style={{ color: 'var(--ink-ghost)' }}>·</span>
          <span style={{ color: 'var(--saffron)', fontSize: 10, fontWeight: 600, letterSpacing: '.04em' }}>
            {regTypeLabel}
          </span>
        </div>

        {/* ECI verified badge */}
        <div style={{
          background: 'var(--emerald-dim)',
          border: '1px solid rgba(16,185,129,0.33)',
          borderRadius: 8, padding: '5px 11px',
          display: 'flex', alignItems: 'center', gap: 5,
          fontSize: 10.5, color: 'var(--emerald)',
        }}>
          🔒 ECI Sourced
        </div>
      </div>
    </header>
  );
}