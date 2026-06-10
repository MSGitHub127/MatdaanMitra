'use client';

import dynamic from 'next/dynamic';
import { useState, useCallback } from 'react';
import type { VoterProfile } from '../../types/voter';
import StatGrid from './StatGrid';
import RegistrationTimeline from './RegistrationTimeline';
import DocumentChecklist from './DocumentChecklist';
import FormCards from './FormCards';

// EROLocator has Mapbox — must be client-only
const EROLocator = dynamic(() => import('./EROLocator'), {
  ssr: false,
  loading: () => (
    <div style={{
      height: 300, background: 'var(--card)', borderRadius: 14,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <p style={{ color: 'var(--ink-faint)', fontSize: 13 }}>Loading map…</p>
    </div>
  ),
});

const TABS = ['Timeline', 'Documents', 'Forms', 'ERO & BLO', 'Grievance'];

const GRIEVANCE_TYPES = [
  { icon: '❌', title: 'Name Missing from Roll', form: 'Form 6 (fresh registration)', desc: 'Never been enrolled at this address', color: 'var(--rose)' },
  { icon: '✏️', title: 'Name Misspelled / Wrong DOB', form: 'Form 8 (correction)', desc: 'Any personal detail errors in the roll', color: 'var(--amber)' },
  { icon: '🏠', title: 'Address Outdated on Roll', form: 'Form 8A (address update)', desc: 'Within same constituency address change', color: 'var(--sapphire)' },
  { icon: '🗑️', title: 'Name on Roll but Moved', form: 'Form 7 (deletion)', desc: 'Remove entry from old constituency', color: 'var(--violet)' },
];

// Issue type → backend key mapping
const ISSUE_KEYS = ['missing_name', 'wrong_details', 'address_update', 'duplicate_entry'];

interface VoterDashboardProps {
  profile: VoterProfile;
  sessionId: string;
  onUpdateChecklist: (checklist: Record<string, boolean>) => void;
  activeTab?: number;
  onTabChange?: (tab: number) => void;
}

export default function VoterDashboard({
  profile, sessionId, onUpdateChecklist, activeTab = 0, onTabChange,
}: VoterDashboardProps) {

  const setTab = (i: number) => onTabChange?.(i);
  const constituency = profile.current_state ?? 'Your Constituency';

  // Grievance letter state
  const [selectedIssue, setSelectedIssue] = useState<number | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  const handleDownloadLetter = useCallback(async () => {
    const issueIndex = selectedIssue ?? 0;
    const issueType = ISSUE_KEYS[issueIndex];
    setPdfLoading(true);
    setPdfError(null);

    try {
      const { getAuth } = await import('firebase/auth');
      const user = getAuth().currentUser;
      if (!user) throw new Error('Not authenticated');
      const token = await user.getIdToken();

      const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';
      const res = await fetch(`${BACKEND_URL}/grievance/letter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ session_id: sessionId, issue_type: issueType }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Request failed (${res.status})`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `voter_complaint_${issueType}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setPdfError(err instanceof Error ? err.message : 'Download failed. Please try again.');
    } finally {
      setPdfLoading(false);
    }
  }, [sessionId, selectedIssue]);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--bg)', overflow: 'hidden' }}>

      {/* ── Stats header — always visible ── */}
      <div style={{ padding: '14px 20px 0', flexShrink: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 12 }}>
          <div>
            <h2 className="font-display" style={{ fontSize: 24, fontWeight: 700, color: 'var(--ink)', lineHeight: 1, letterSpacing: '-.02em' }}>
              Voter Dashboard
            </h2>
            <div style={{ fontSize: 11.5, color: 'var(--ink-dim)', marginTop: 4, display: 'flex', alignItems: 'center', gap: 7 }}>
              <span>{profile.current_state ?? 'India'}</span>
              {profile.current_pincode && <>
                <span style={{ color: 'var(--ink-ghost)' }}>·</span>
                <span style={{ color: 'var(--saffron)' }}>PIN {profile.current_pincode}</span>
              </>}
            </div>
          </div>
          <div style={{
            fontSize: 10.5, color: 'var(--saffron-warm)',
            background: 'var(--saffron-trace)',
            border: '1px solid rgba(249,115,22,0.22)',
            borderRadius: 8, padding: '5px 12px',
          }}>
            Phase 3 · MH-2026
          </div>
        </div>

        <StatGrid profile={profile} />
      </div>

      {/* ── Tab bar ── */}
      <div style={{
        borderBottom: '1px solid var(--border)',
        flexShrink: 0, padding: '0 20px',
        display: 'flex', gap: 2, marginTop: 14,
      }}>
        {TABS.map((label, i) => (
          <button key={label} onClick={() => setTab(i)} style={{
            all: 'unset', cursor: 'pointer',
            padding: '9px 16px', fontSize: 12, fontWeight: 500,
            color: activeTab === i ? 'var(--saffron-warm)' : 'var(--ink-ghost)',
            borderBottom: `2px solid ${activeTab === i ? 'var(--saffron)' : 'transparent'}`,
            background: activeTab === i ? 'var(--saffron-trace)' : 'transparent',
            borderRadius: '8px 8px 0 0', transition: 'all .15s', whiteSpace: 'nowrap',
          }}
            onMouseEnter={e => { if (activeTab !== i) e.currentTarget.style.color = 'var(--saffron-warm)'; }}
            onMouseLeave={e => { if (activeTab !== i) e.currentTarget.style.color = 'var(--ink-ghost)'; }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Tab content ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '18px 20px 28px' }}>

        {/* ── TAB 0: TIMELINE ── */}
        {activeTab === 0 && (
          <div className="fade-up">
            <RegistrationTimeline profile={profile} />
          </div>
        )}

        {/* ── TAB 1: DOCUMENTS ── */}
        {activeTab === 1 && (
          <div className="fade-up">
            <DocumentChecklist
              checklist={profile.checklist || {}}
              onUpdate={onUpdateChecklist}
            />
          </div>
        )}

        {/* ── TAB 2: FORMS ── */}
        {activeTab === 2 && (
          <div className="fade-up">
            <FormCards profile={profile} />
          </div>
        )}

        {/* ── TAB 3: ERO & BLO ── */}
        {activeTab === 3 && (
          <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* ERO Locator */}
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
              <div style={{ padding: '16px 18px 12px' }}>
                <h3 className="font-display" style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink)', marginBottom: 3 }}>
                  ERO Office Locator
                </h3>
                <p style={{ fontSize: 11.5, color: 'var(--ink-dim)' }}>
                  Find your nearest Electoral Registration Officer via Mapbox
                </p>
              </div>
              <EROLocator />
            </div>

            {/* BLO information */}
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: 18 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 14 }}>
                <div style={{
                  width: 46, height: 46, borderRadius: 12,
                  background: 'var(--emerald-dim)',
                  border: '1px solid rgba(16,185,129,0.3)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 22, flexShrink: 0,
                }}>🧑‍💼</div>
                <div style={{ flex: 1 }}>
                  <h3 className="font-display" style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink)' }}>
                    Booth Level Officer (BLO)
                  </h3>
                  <p style={{ fontSize: 11.5, color: 'var(--ink-dim)', marginTop: 2 }}>
                    {constituency} Assembly Segment
                  </p>
                </div>
                <a
                  href="tel:1950"
                  style={{
                    textDecoration: 'none',
                    background: 'var(--emerald-dim)',
                    border: '1px solid rgba(16,185,129,0.4)',
                    color: 'var(--emerald)',
                    borderRadius: 9, padding: '8px 15px',
                    fontSize: 11.5, fontWeight: 600,
                  }}
                >
                  Contact BLO
                </a>
              </div>

              <div style={{ background: 'var(--surface)', borderRadius: 10, padding: '11px 13px' }}>
                {[
                  ['What they do', 'Physically visits your address to verify you actually reside there'],
                  ['When to expect', 'Within 30 days of your Form 6 submission'],
                  ['What to keep ready', 'Original Aadhaar, address proof, and a copy of your submitted Form 6'],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', gap: 10, marginBottom: 8, alignItems: 'flex-start' }}>
                    <span style={{ fontSize: 11, color: 'var(--ink-ghost)', minWidth: 110, flexShrink: 0 }}>{k}</span>
                    <span style={{ fontSize: 11.5, color: 'var(--ink-dim)', lineHeight: 1.5 }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 4: GRIEVANCE ── */}
        {activeTab === 4 && (
          <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* Helpline card */}
            <div style={{
              background: 'linear-gradient(135deg, var(--amber-dim), var(--card))',
              border: '1px solid rgba(251,191,36,0.33)',
              borderRadius: 14, padding: 18,
              display: 'flex', gap: 14, alignItems: 'center',
            }}>
              <div style={{
                width: 52, height: 52, borderRadius: 14,
                background: 'var(--amber-dim)', border: '1px solid rgba(251,191,36,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 26, flexShrink: 0,
              }}>📞</div>
              <div style={{ flex: 1 }}>
                <div className="font-display" style={{ fontSize: 15, fontWeight: 700, color: 'var(--ink)' }}>
                  National Voter Helpline
                </div>
                <div className="font-display" style={{ fontSize: 28, fontWeight: 700, color: 'var(--amber)', lineHeight: 1.1 }}>
                  1950
                </div>
                <div style={{ fontSize: 11, color: 'var(--ink-dim)', marginTop: 3 }}>
                  Toll-free · Mon–Sat · 8 AM – 8 PM · All languages
                </div>
              </div>
              <a href="tel:1950" style={{
                textDecoration: 'none',
                background: 'var(--amber)', color: '#030508',
                borderRadius: 10, padding: '10px 18px',
                fontSize: 13, fontWeight: 700, flexShrink: 0,
              }}>
                Call Now
              </a>
            </div>

            {/* Issue types */}
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: 18 }}>
              <h3 className="font-display" style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)', marginBottom: 14 }}>
                What Issue Are You Facing?
              </h3>
              <p style={{ fontSize: 11, color: 'var(--ink-dim)', marginBottom: 10 }}>
                Select your issue type, then generate your pre-filled complaint letter.
              </p>
              {GRIEVANCE_TYPES.map((g, i) => (
                <div key={g.title} onClick={() => setSelectedIssue(i)} style={{
                  display: 'flex', gap: 12, padding: '11px 12px',
                  borderRadius: 10,
                  background: selectedIssue === i ? 'var(--violet-dim)' : 'var(--surface)',
                  border: `1px solid ${selectedIssue === i ? 'rgba(167,139,250,0.55)' : 'var(--border)'}`,
                  marginBottom: 7, cursor: 'pointer', transition: 'all .14s',
                }}
                  onMouseEnter={e => { if (selectedIssue !== i) e.currentTarget.style.borderColor = 'rgba(249,115,22,0.3)'; }}
                  onMouseLeave={e => { if (selectedIssue !== i) e.currentTarget.style.borderColor = selectedIssue === i ? 'rgba(167,139,250,0.55)' : 'var(--border)'; }}
                >
                  <span style={{ fontSize: 20, flexShrink: 0, marginTop: 1 }}>{g.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>{g.title}</div>
                    <div style={{ fontSize: 11, color: 'var(--ink-dim)', marginTop: 2 }}>{g.desc}</div>
                  </div>
                  <div style={{ flexShrink: 0, textAlign: 'right' }}>
                    <div style={{ fontSize: 10, color: g.color, fontWeight: 700, letterSpacing: '.04em' }}>{g.form}</div>
                    <a
                      href="https://eci.gov.in"
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={e => e.stopPropagation()}
                      style={{ fontSize: 10, color: 'var(--ink-ghost)', marginTop: 2, display: 'block', textDecoration: 'none' }}
                    >
                      Download form →
                    </a>
                  </div>
                </div>
              ))}
            </div>

            {/* Grievance letter generator */}
            <div style={{
              background: 'linear-gradient(135deg, var(--violet-dim), var(--card))',
              border: '1px solid rgba(167,139,250,0.33)',
              borderRadius: 14, padding: 18,
            }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 12 }}>
                <span style={{ fontSize: 22 }}>📝</span>
                <div>
                  <div className="font-display" style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink)' }}>
                    Grievance Letter Generator
                  </div>
                  <p style={{ fontSize: 11.5, color: 'var(--ink-dim)', marginTop: 4, lineHeight: 1.6 }}>
                    {selectedIssue !== null
                      ? `Generating letter for: ${GRIEVANCE_TYPES[selectedIssue].title}`
                      : 'Select an issue above, then click to generate your pre-filled complaint letter.'}
                  </p>
                </div>
              </div>

              {pdfError && (
                <div style={{ marginBottom: 10, padding: '8px 12px', background: 'var(--rose-dim)', border: '1px solid rgba(251,113,133,0.3)', borderRadius: 9, fontSize: 11.5, color: 'var(--rose)' }}>
                  {pdfError}
                </div>
              )}

              <button
                onClick={handleDownloadLetter}
                disabled={pdfLoading}
                style={{
                  all: 'unset',
                  cursor: pdfLoading ? 'wait' : 'pointer',
                  width: '100%',
                  background: selectedIssue !== null
                    ? 'linear-gradient(135deg, var(--violet), #6D28D9)'
                    : 'var(--card)',
                  color: selectedIssue !== null ? '#fff' : 'var(--ink-ghost)',
                  borderRadius: 10, padding: '11px',
                  textAlign: 'center', fontSize: 13, fontWeight: 700,
                  boxShadow: selectedIssue !== null ? '0 4px 16px var(--violet-dim)' : 'none',
                  border: `1px solid ${selectedIssue !== null ? 'transparent' : 'var(--border)'}`,
                  opacity: pdfLoading ? 0.6 : 1,
                  transition: 'all .15s',
                }}
                onMouseEnter={e => { if (!pdfLoading && selectedIssue !== null) e.currentTarget.style.opacity = '0.88'; }}
                onMouseLeave={e => { if (!pdfLoading) e.currentTarget.style.opacity = '1'; }}
              >
                {pdfLoading ? '⏳ Generating PDF…' : '✨ Generate My Complaint Letter (PDF)'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer status bar */}
      <footer style={{
        height: 28, flexShrink: 0,
        background: 'var(--surface)',
        borderTop: '1px solid var(--border)',
        display: 'flex', alignItems: 'center',
        padding: '0 20px', gap: 14,
        fontSize: 10, color: 'var(--ink-ghost)',
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--emerald)' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--emerald)', animation: 'pulse 1.8s ease infinite', display: 'inline-block' }} />
          RAG active
        </span>
        <span>·</span>
        <span>ECI corpus · Synced Apr 2026</span>
        <span>·</span>
        <span>Gemini 1.5 Pro · text-embedding-004</span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span>Not affiliated with any political party</span>
          <span>·</span>
          <span style={{ color: 'var(--emerald)' }}>Official ECI data only</span>
        </div>
      </footer>
    </div>
  );
}