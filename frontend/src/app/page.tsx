'use client';

import { useState, useEffect } from 'react';
import { ensureAuth } from '../lib/firebase';
import { generateSessionId } from '../lib/utils';
import { useChat } from '../hooks/useChat';
import { useVoterProfile } from '../hooks/useVoterProfile';
import VoterSidebar from '../components/sidebar/VoterSidebar';
import ChatPanel from '../components/chat/ChatPanel';
import VoterDashboard from '../components/dashboard/VoterDashboard';

export default function Home() {
  const [sessionId, setSessionId] = useState<string>('');
  const [language, setLanguage] = useState('en');
  const [isInitialized, setIsInitialized] = useState(false);

  const { messages, sendMessage, isLoading } = useChat(sessionId, language);
  const { profile, updateChecklist } = useVoterProfile(sessionId);

  useEffect(() => {
    const init = async () => {
      const uid = await ensureAuth();
      const newSessionId = generateSessionId();
      setSessionId(newSessionId);
      setIsInitialized(true);
    };

    init();
  }, []);

  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-screen bg-bg">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-saffron border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-ink-dim">Initializing Matdaan Mitra...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-bg">
      {/* Left Sidebar - Voter DNA */}
      <VoterSidebar
        profile={profile}
        sessionId={sessionId}
        language={language}
        onLanguageChange={setLanguage}
      />

      {/* Center Panel - Chat */}
      <ChatPanel
        messages={messages}
        onSendMessage={sendMessage}
        isLoading={isLoading}
        language={language}
      />

      {/* Right Dashboard - Live Voter Dashboard */}
      <VoterDashboard
        profile={profile}
        onUpdateChecklist={updateChecklist}
      />
    </div>
  );
}
