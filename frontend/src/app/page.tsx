'use client';

import { useState, useEffect } from 'react';
import { ensureAuth } from '../lib/firebase';
import { generateSessionId } from '../lib/utils';
import { useChat } from '../hooks/useChat';
import { useVoterProfile } from '../hooks/useVoterProfile';
import Header from '../components/layout/Header';
import VoterSidebar from '../components/sidebar/VoterSidebar';
import ChatPanel from '../components/chat/ChatPanel';
import VoterDashboard from '../components/dashboard/VoterDashboard';

export default function Home() {
  const [sessionId, setSessionId] = useState('');
  const [language, setLanguage] = useState('en');
  const [dashTab, setDashTab] = useState(0);
  const [isInitialized, setIsInitialized] = useState(false);

  const { messages, sendMessage, isLoading } = useChat(sessionId, language);
  const { profile, updateChecklist } = useVoterProfile(sessionId);

  useEffect(() => {
    (async () => {
      await ensureAuth();
      setSessionId(generateSessionId());
      setIsInitialized(true);
    })();
  }, []);

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-screen bg-bg">
        <div className="text-center">
          <div
            className="w-12 h-12 rounded-full mx-auto mb-4 animate-spin"
            style={{
              border: '3px solid rgba(249,115,22,0.2)',
              borderTop: '3px solid #F97316',
            }}
          />
          <p style={{ color: 'var(--ink-dim)', fontSize: 14 }}>
            Initializing Matdaan Mitra…
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <Header
        profile={profile}
        language={language}
        onLanguageChange={setLanguage}
      />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative', zIndex: 1 }}>
        <VoterSidebar
          profile={profile}
          sessionId={sessionId}
          language={language}
          onNavigate={setDashTab}
        />
        <ChatPanel
          messages={messages}
          onSendMessage={sendMessage}
          isLoading={isLoading}
          language={language}
        />
        <VoterDashboard
          profile={profile}
          onUpdateChecklist={updateChecklist}
          activeTab={dashTab}
          onTabChange={setDashTab}
        />
      </div>
    </div>
  );
}