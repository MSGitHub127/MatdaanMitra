'use client';

import { useState, useCallback } from 'react';
import type { VoterProfile } from '../../types/voter';
import { getVoterStatus, ApiError } from '../../lib/api';

interface VoterSidebarProps {
  profile: VoterProfile;
  sessionId: string;
  language: string;
  /** Callback to switch the dashboard to a specific tab (0–4). */
  onNavigate: (tab: number) => void;
}

type SideTab = 'profile' | 'lookup' | 'phases';

/* ── Dot ── */
function Dot({ pulse = false, color = '#10B981' }: { pulse?: boolean; color?: string }) {
  return (
    <span style={{
      width: 7, height: 7, borderRadius: '50%', background: color,
      display: 'inline-block', flexShrink: 0,
      ...(pulse ? { animation: 'pulse 1.8s ease infinite' } : {}),
    }} />
  );
}

export default function VoterSidebar({ profile, sessionId, language, onNavigate }: VoterSidebarProps) {
  const [tab, setTab] = useState<SideTab>('profile');

  // Voter lookup state
  const [epic, setEpic] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupResult, setLookupResult] = useState<any>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const completionPct = profile.checklist
    ? Object.values(profile.checklist).filter(Boolean).length /
    Math.max(Object.values(profile.checklist).length, 1)
    : 0;
  const doneCount = profile.checklist
    ? Object.values(profile.checklist).filter(Boolean).length : 0;
  const totalDocs = profile.checklist ? Object.keys(profile.checklist).length : 5;

  const initials = profile.name
    ? profile.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'MM';

  const handleLookup = useCallback(async () => {
    if (!epic.trim()) return;
    setLookupLoading(true);
    setLookupError(null);
    setLookupResult(null);
    try {
      const result = await getVoterStatus(epic.trim());
      setLookupResult(result);
    } catch (err) {
      setLookupError(
        err instanceof ApiError ? err.message : 'Lookup failed. Please try again.'
      );
    } finally {
      setLookupLoading(false);
    }
  }, [epic]);

  const QUICK_NAV = [
    { icon: '📋', label: 'Form 6 — New Registration', sub: 'Download · ERO submission', tab: 2 },
    { icon: '📄', label: 'Form 7 — Delete old entry', sub: 'Dual enrollment prevention', tab: 2 },
    { icon: '🗺️', label: 'Find Nearest ERO', sub: 'Interactive map locator', tab: 3 },
    { icon: '🧑‍💼', label: 'Contact BLO', sub: 'Address verification officer', tab: 3 },
    { icon: '📣', label: 'File a Grievance', sub: 'Form 8 · Helpline 1950', tab: 4 },
  ];

  return (
    <aside style={{
      width: 248, flexShrink: 0,
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>

      {/* ── Sub-tab icons ── */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        {([['profile', '👤'], ['lookup', '🔍'], ['phases', '📅']] as [SideTab, string][]).map(([key, icon]) => (
          <button key={key} onClick={() => setTab(key)} title={key} style={{
            all: 'unset', cursor: 'pointer', flex: 1,
            padding: '9px 0', textAlign: 'center', fontSize: 16,
            borderBottom: `2px solid ${tab === key ? 'var(--saffron)' : 'transparent'}`,
            background: tab === key ? 'var(--saffron-trace)' : 'transparent',
            transition: 'all .15s',
          }}>
            {icon}
          </button>
        ))}
      </div>

      {/* ══════════════════════════
          TAB: PROFILE
      ══════════════════════════ */}
      {tab === 'profile' && (
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>

          {/* Voter hero */}
          <div style={{ padding: '18px 16px 14px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', gap: 11, alignItems: 'center', marginBottom: 14 }}>
              <div style={{
                width: 46, height: 46, borderRadius: '50%', flexShrink: 0, position: 'relative',
                background: 'linear-gradient(135deg, var(--saffron), var(--saffron-warm))',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'Fraunces, serif', fontSize: 18, fontWeight: 700, color: '#fff',
                animation: 'glowRing 3s ease infinite',
              }}>
                {initials}
                <span style={{
                  position: 'absolute', bottom: 1, right: 1,
                  width: 10, height: 10, borderRadius: '50%',
                  background: '#10B981', border: '2px solid var(--surface)',
                  animation: 'pulse 2s infinite',
                }} />
              </div>
              <div>
                <div className="font-display" style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)' }}>
                  {profile.name ?? 'Your Profile'}
                </div>
                <div style={{ fontSize: 10, color: 'var(--ink-ghost)', letterSpacing: '.08em', marginTop: 2 }}>
                  VOTER PROFILE · ACTIVE
                </div>
              </div>
            </div>

            {/* Migration card */}
            {(profile.current_state || profile.previous_state) && (
              <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 11, overflow: 'hidden' }}>
                <div style={{ padding: '8px 11px 6px', fontSize: 9, color: 'var(--ink-ghost)', letterSpacing: '.1em' }}>
                  REGISTRATION JOURNEY
                </div>
                <div style={{ display: 'flex', alignItems: 'stretch', padding: '0 11px 10px', gap: 8 }}>
                  <div style={{ flex: 1, background: 'var(--rose-dim)', border: '1px solid rgba(251,113,133,0.33)', borderRadius: 8, padding: '8px 9px' }}>
                    <div style={{ fontSize: 8.5, color: 'var(--rose)', letterSpacing: '.08em', fontWeight: 700 }}>FROM</div>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink)', marginTop: 3 }}>
                      {profile.previous_state ?? '—'}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--ink-dim)', marginTop: 1 }}>
                      {profile.previous_constituency ?? 'Previous address'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', fontSize: 18, color: 'var(--saffron)' }}>→</div>
                  <div style={{ flex: 1, background: 'var(--emerald-dim)', border: '1px solid rgba(16,185,129,0.33)', borderRadius: 8, padding: '8px 9px' }}>
                    <div style={{ fontSize: 8.5, color: 'var(--emerald)', letterSpacing: '.08em', fontWeight: 700 }}>TO</div>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink)', marginTop: 3 }}>
                      {profile.current_state ?? '—'}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--ink-dim)', marginTop: 1 }}>
                      {profile.current_pincode ? `Pincode ${profile.current_pincode}` : 'Current address'}
                    </div>
                  </div>
                </div>
                <div style={{ borderTop: '1px solid var(--border)', padding: '7px 11px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 10, color: 'var(--ink-dim)' }}>Registration type</span>
                  <span style={{ fontSize: 10, color: 'var(--saffron)', fontWeight: 700, letterSpacing: '.06em' }}>
                    {(profile.registration_type ?? 'N/A').toUpperCase().replace('_', '-')}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Document progress */}
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--ink)' }}>Document Progress</span>
              <span style={{ fontSize: 10.5, color: 'var(--ink-dim)' }}>{doneCount}/{totalDocs}</span>
            </div>
            <div style={{ height: 6, background: 'var(--border)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${completionPct * 100}%`,
                background: 'linear-gradient(90deg, var(--saffron), var(--saffron-warm))',
                borderRadius: 4,
                transition: 'width .6s cubic-bezier(.34,1.56,.64,1)',
                boxShadow: '0 0 8px var(--saffron-glow)',
              }} />
            </div>
          </div>

          {/* Quick nav */}
          <div style={{ padding: '10px 10px', flex: 1, overflowY: 'auto' }}>
            <div style={{ fontSize: 9, color: 'var(--ink-ghost)', letterSpacing: '.1em', padding: '4px 6px 7px' }}>
              QUICK ACCESS
            </div>
            {QUICK_NAV.map((item, i) => (
              <button key={i} onClick={() => onNavigate(item.tab)} style={{
                all: 'unset', cursor: 'pointer',
                display: 'flex', gap: 10, padding: '8px 8px',
                borderRadius: 9, width: '100%',
                transition: 'all .14s', marginBottom: 2,
              }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--saffron-dim)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <span style={{ fontSize: 16, flexShrink: 0 }}>{item.icon}</span>
                <div>
                  <div style={{ fontSize: 11.5, fontWeight: 500, color: 'var(--ink)' }}>{item.label}</div>
                  <div style={{ fontSize: 10, color: 'var(--ink-ghost)', marginTop: 1 }}>{item.sub}</div>
                </div>
              </button>
            ))}
          </div>

          {/* Phase badge */}
          <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border)', flexShrink: 0 }}>
            <div style={{ background: 'var(--saffron-trace)', border: '1px solid rgba(249,115,22,0.22)', borderRadius: 11, padding: '11px 13px' }}>
              <div style={{ fontSize: 9, color: 'var(--saffron)', letterSpacing: '.12em', fontWeight: 700 }}>ELECTION PHASE</div>
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, marginTop: 5 }}>
                <span className="font-display" style={{ fontSize: 34, fontWeight: 700, color: 'var(--saffron-warm)', lineHeight: 1 }}>3</span>
                <span style={{ fontSize: 12, color: 'var(--ink-dim)', paddingBottom: 4 }}>of 7 · MH Assembly 2026</span>
              </div>
              <div style={{ height: 3, background: 'var(--border)', borderRadius: 2, marginTop: 8, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: '42%', background: 'linear-gradient(90deg,var(--saffron),var(--saffron-warm))', borderRadius: 2 }} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════
          TAB: VOTER LOOKUP
      ══════════════════════════ */}
      {tab === 'lookup' && (
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 14px' }}>
          <div className="font-display" style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)', marginBottom: 4 }}>
            Live Voter Status
          </div>
          <p style={{ fontSize: 11, color: 'var(--ink-dim)', marginBottom: 14, lineHeight: 1.5 }}>
            Enter your EPIC number to verify enrollment via the ECI electoral search API.
          </p>

          <label style={{ fontSize: 10, color: 'var(--ink-ghost)', letterSpacing: '.08em', display: 'block', marginBottom: 5 }}>
            EPIC NUMBER
          </label>
          <input
            value={epic}
            onChange={e => setEpic(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && handleLookup()}
            placeholder="e.g. BR/14/023/123456"
            style={{
              width: '100%', background: 'var(--card)',
              border: '1px solid var(--border-fine)',
              borderRadius: 9, padding: '9px 11px',
              color: 'var(--ink)', fontSize: 12,
              fontFamily: 'Instrument Sans, sans-serif',
              outline: 'none', marginBottom: 10,
            }}
          />

          <button
            onClick={handleLookup}
            disabled={!epic.trim() || lookupLoading}
            style={{
              all: 'unset', cursor: epic.trim() ? 'pointer' : 'not-allowed',
              width: '100%',
              background: epic.trim()
                ? 'linear-gradient(135deg, var(--saffron), var(--saffron-warm))'
                : 'var(--card)',
              color: epic.trim() ? '#030508' : 'var(--ink-ghost)',
              borderRadius: 10, padding: '11px',
              textAlign: 'center', fontSize: 13, fontWeight: 700,
              transition: 'all .15s',
              boxShadow: epic.trim() ? '0 4px 16px var(--saffron-dim)' : 'none',
            }}
          >
            {lookupLoading ? '🔄  Calling ECI API…' : '🔍  Verify Enrollment'}
          </button>

          {lookupError && (
            <div style={{
              marginTop: 12, padding: '10px 12px',
              background: 'var(--rose-dim)', border: '1px solid rgba(251,113,133,0.4)',
              borderRadius: 10, fontSize: 11.5, color: 'var(--rose)',
            }}>
              {lookupError}
            </div>
          )}

          {lookupResult && (
            <div className="slide-dn" style={{
              marginTop: 14,
              background: lookupResult.nvsp_redirect
                ? 'var(--amber-dim)'
                : lookupResult.found
                  ? 'var(--emerald-dim)'
                  : 'var(--rose-dim)',
              border: `1px solid ${lookupResult.nvsp_redirect
                ? 'rgba(251,191,36,0.4)'
                : lookupResult.found
                  ? 'rgba(16,185,129,0.4)'
                  : 'rgba(251,113,133,0.4)'
                }`,
              borderRadius: 11, padding: '12px 13px',
            }}>
              {/* NVSP Redirect — ECI API blocked */}
              {lookupResult.nvsp_redirect && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                    <span style={{ fontSize: 18 }}>🔗</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--amber)' }}>
                      Verify on Official NVSP Portal
                    </span>
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--ink-dim)', marginBottom: 10, lineHeight: 1.5 }}>
                    Direct ECI API lookup is currently unavailable. Click below to verify your voter status on the official NVSP portal.
                  </p>
                  <a
                    href={lookupResult.nvsp_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                      background: 'var(--amber)', color: '#030508',
                      borderRadius: 9, padding: '9px 14px',
                      textDecoration: 'none', fontSize: 12, fontWeight: 700,
                    }}
                  >
                    🗳️ Open NVSP.in →
                  </a>
                </>
              )}

              {/* Found on roll */}
              {!lookupResult.nvsp_redirect && lookupResult.found && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                    <span style={{ fontSize: 18 }}>✅</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--emerald)' }}>
                      Found on Electoral Roll
                    </span>
                  </div>
                  {[
                    ['Name', lookupResult.name],
                    ['Constituency', lookupResult.assembly_constituency],
                    ['Polling Station', lookupResult.polling_station],
                  ].filter(([, v]) => v).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 11 }}>
                      <span style={{ color: 'var(--ink-dim)' }}>{k}</span>
                      <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{v}</span>
                    </div>
                  ))}
                </>
              )}

              {/* Not found */}
              {!lookupResult.nvsp_redirect && lookupResult.found === false && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <span style={{ fontSize: 18 }}>❌</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--rose)' }}>
                      Not Found on Roll
                    </span>
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--rose)', marginBottom: 8 }}>
                    {lookupResult.message || 'EPIC not found in ECI database.'}
                  </p>
                  {lookupResult.nvsp_url && (
                    <a href={lookupResult.nvsp_url} target="_blank" rel="noopener noreferrer"
                      style={{ fontSize: 11, color: 'var(--ink-dim)', textDecoration: 'underline' }}>
                      Verify on NVSP.in →
                    </a>
                  )}
                </>
              )}

              <div style={{ marginTop: 8, fontSize: 9.5, color: 'var(--ink-ghost)' }}>
                Source: ECI Electoral Search · Live result
              </div>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════
          TAB: PHASE CALENDAR
      ══════════════════════════ */}
      {tab === 'phases' && (
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 14px' }}>
          <div className="font-display" style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink)', marginBottom: 4 }}>
            MH Assembly 2026
          </div>
          <p style={{ fontSize: 11, color: 'var(--ink-dim)', marginBottom: 14 }}>
            Constituency-specific deadlines
          </p>
          {[
            { phase: 1, cons: 'Mumbai South', date: 'Oct 5', reg: 'Aug 25', active: false },
            { phase: 2, cons: 'Pune Central', date: 'Oct 12', reg: 'Sep 5', active: false },
            { phase: 3, cons: 'Kothrud (Yours)', date: 'Oct 20', reg: 'Sep 30', active: true },
            { phase: 4, cons: 'Nashik East', date: 'Oct 27', reg: 'Oct 7', active: false },
            { phase: 5, cons: 'Nagpur West', date: 'Nov 3', reg: 'Oct 14', active: false },
          ].map(p => (
            <div key={p.phase} style={{
              marginBottom: 8,
              background: p.active ? 'var(--saffron-trace)' : 'var(--card)',
              border: `1px solid ${p.active ? 'rgba(249,115,22,0.44)' : 'var(--border)'}`,
              borderRadius: 10, padding: '10px 12px',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                <div>
                  <div style={{ fontSize: 9, color: p.active ? 'var(--saffron)' : 'var(--ink-ghost)', letterSpacing: '.08em', fontWeight: 700 }}>
                    PHASE {p.phase}
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: p.active ? 'var(--ink)' : 'var(--ink-dim)', marginTop: 1 }}>
                    {p.cons}
                  </div>
                </div>
                {p.active && (
                  <span style={{ fontSize: 9, background: 'var(--saffron-dim)', color: 'var(--saffron)', padding: '2px 8px', borderRadius: 5, fontWeight: 700 }}>
                    YOURS
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 12, fontSize: 10.5 }}>
                <div><span style={{ color: 'var(--ink-ghost)' }}>Voting: </span><span style={{ color: 'var(--ink)' }}>{p.date}</span></div>
                <div><span style={{ color: 'var(--ink-ghost)' }}>Reg. deadline: </span><span style={{ color: p.active ? 'var(--saffron)' : 'var(--ink-dim)' }}>{p.reg}</span></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Session footer */}
      <div style={{ padding: '8px 14px', borderTop: '1px solid var(--border)', flexShrink: 0 }}>
        <p className="font-mono" style={{ fontSize: 9, color: 'var(--ink-ghost)' }}>
          Session: {sessionId.slice(-8) || '—'}
        </p>
      </div>
    </aside>
  );
}