'use client';

import { useState, useEffect } from 'react';
import { onAuthChange, ensureAuth } from '../lib/firebase';
import { generateSessionId } from '../lib/utils';
import { useChat } from '../hooks/useChat';
import { useVoterProfile } from '../hooks/useVoterProfile';
import { ErrorBoundary } from '../components/ui/ErrorBoundary';
import Header from '../components/layout/Header';
import VoterSidebar from '../components/sidebar/VoterSidebar';
import ChatPanel from '../components/chat/ChatPanel';
import VoterDashboard from '../components/dashboard/VoterDashboard';
import LoginScreen from '../components/auth/LoginScreen';

// ── Mobile tab bar ────────────────────────────────────────────────────────────

type MobileTab = 'sidebar' | 'chat' | 'dashboard';

const MOBILE_TABS: { id: MobileTab; icon: string; label: string }[] = [
  { id: 'sidebar', icon: '👤', label: 'Profile' },
  { id: 'chat', icon: '💬', label: 'Chat' },
  { id: 'dashboard', icon: '📋', label: 'Dashboard' },
];

// ── Loading screen ────────────────────────────────────────────────────────────

function LoadingScreen() {
  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 16,
    }}>
      <div style={{
        width: 48, height: 48, borderRadius: '50%',
        border: '3px solid rgba(249,115,22,0.2)',
        borderTop: '3px solid #F97316',
        animation: 'spin 0.9s linear infinite',
      }} />
      <p style={{ color: 'var(--ink-dim)', fontSize: 13 }}>
        Initializing Matdaan Mitra…
      </p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── Main app shell (rendered after auth) ──────────────────────────────────────

function AppShell() {
  const [sessionId] = useState(generateSessionId);
  const [language, setLanguage] = useState('en');
  const [dashTab, setDashTab] = useState(0);
  const [mobileTab, setMobileTab] = useState<MobileTab>('chat');

  const { messages, sendMessage, isLoading } = useChat(sessionId, language);
  const { profile, updateChecklist } = useVoterProfile(sessionId);

  // When sidebar quick-nav fires, switch both the dashboard tab
  // AND the mobile view to the dashboard panel
  const handleNavigate = (tab: number) => {
    setDashTab(tab);
    setMobileTab('dashboard');
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', overflow: 'hidden',
    }}>
      {/* Global header with language selector + voter pill */}
      <Header
        profile={profile}
        language={language}
        onLanguageChange={setLanguage}
      />

      {/* ── Three-column desktop layout ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>

        <div className="panel-sidebar">
          <VoterSidebar
            profile={profile}
            sessionId={sessionId}
            language={language}
            onNavigate={handleNavigate}
          />
        </div>

        <div className="panel-chat">
          <ChatPanel
            messages={messages}
            onSendMessage={sendMessage}
            isLoading={isLoading}
            language={language}
          />
        </div>

        <div
          className="panel-dashboard"
          style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
        >
          <VoterDashboard
            profile={profile}
            sessionId={sessionId}
            onUpdateChecklist={updateChecklist}
            activeTab={dashTab}
            onTabChange={setDashTab}
          />
        </div>
      </div>

      {/* ── Mobile tab bar (hidden on desktop via CSS) ── */}
      <nav className="mobile-tab-bar">
        {MOBILE_TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setMobileTab(tab.id)}
            style={{
              all: 'unset', cursor: 'pointer',
              flex: 1, display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
              gap: 3, padding: '8px 0',
              color: mobileTab === tab.id ? 'var(--saffron)' : 'var(--ink-ghost)',
              fontSize: 10,
              fontWeight: mobileTab === tab.id ? 700 : 400,
              borderTop: `2px solid ${mobileTab === tab.id ? 'var(--saffron)' : 'transparent'}`,
              transition: 'all .15s',
            }}
          >
            <span style={{ fontSize: 20 }}>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>

      {/* ── Responsive CSS ── */}
      <style>{`
        /* ── Desktop (≥ 1025px): full 3-column layout ── */
        .panel-sidebar   { width: 248px; flex-shrink: 0; display: flex; flex-direction: column; }
        .panel-chat      { width: 420px; flex-shrink: 0; display: flex; flex-direction: column; }
        .panel-dashboard { min-width: 0; }
        .mobile-tab-bar  { display: none; }

        /* ── Tablet (768–1024px): hide sidebar ── */
        @media (max-width: 1024px) {
          .panel-sidebar { display: none !important; }
          .panel-chat    { width: 360px; }
        }

        /* ── Mobile (≤ 700px): single panel + bottom tab bar ── */
        @media (max-width: 700px) {
          .panel-sidebar,
          .panel-chat,
          .panel-dashboard { display: none !important; }

          /* Show only the currently selected mobile panel */
          .panel-${mobileTab} {
            display: flex !important;
            flex: 1;
            width: 100% !important;
            min-width: 0;
          }

          .mobile-tab-bar {
            display: flex;
            background: var(--surface);
            border-top: 1px solid var(--border);
            flex-shrink: 0;
          }
        }
      `}</style>
    </div>
  );
}

// ── Root page component ───────────────────────────────────────────────────────

type AuthState = 'loading' | 'unauthenticated' | 'authenticated';

export default function Home() {
  const [authState, setAuthState] = useState<AuthState>('loading');

  useEffect(() => {
    // Subscribe to Firebase auth state changes
    const unsubscribe = onAuthChange((user) => {
      setAuthState(user ? 'authenticated' : 'unauthenticated');
    });

    // Attempt silent anonymous sign-in on first load.
    // If Firebase is misconfigured this throws, which the ErrorBoundary catches.
    ensureAuth()
      .then(() => setAuthState('authenticated'))
      .catch(() => setAuthState('unauthenticated'));

    return unsubscribe;
  }, []);

  return (
    <ErrorBoundary>
      {authState === 'loading' && <LoadingScreen />}
      {authState === 'unauthenticated' && (
        <LoginScreen onAuthenticated={(_uid, _isAnonymous) => setAuthState('authenticated')} />
      )}
      {authState === 'authenticated' && (
        // Second ErrorBoundary so an AppShell crash doesn't hide the outer UI
        <ErrorBoundary>
          <AppShell />
        </ErrorBoundary>
      )}
    </ErrorBoundary>
  );
}