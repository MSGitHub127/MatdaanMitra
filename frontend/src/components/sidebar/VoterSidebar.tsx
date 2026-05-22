import { VoterProfile } from '../../types/voter';
import ProfileCard from './ProfileCard';
import MigrationPath from './MigrationPath';
import QuickNav from './QuickNav';

interface VoterSidebarProps {
  profile: VoterProfile;
  sessionId: string;
  language: string;
  onLanguageChange: (lang: string) => void;
}

const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'हिंदी' },
  { code: 'mr', name: 'मराठी' },
  { code: 'ta', name: 'தமிழ்' },
  { code: 'te', name: 'తెలుగు' },
  { code: 'bn', name: 'বাংলা' },
  { code: 'kn', name: 'ಕನ್ನಡ' },
];

export default function VoterSidebar({
  profile,
  sessionId,
  language,
  onLanguageChange,
}: VoterSidebarProps) {
  return (
    <aside className="w-60 bg-surface border-r border-border flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h1 className="font-display text-xl font-semibold text-ink">Matdaan Mitra</h1>
        <p className="text-xs text-ink-dim mt-1">मतदान मित्र</p>
      </div>

      {/* Profile Card */}
      <div className="p-4">
        <ProfileCard profile={profile} />
      </div>

      {/* Migration Path */}
      {profile.registration_type && (
        <div className="px-4 pb-4">
          <MigrationPath profile={profile} />
        </div>
      )}

      {/* Language Selector */}
      <div className="px-4 pb-4">
        <label className="text-xs text-ink-faint uppercase tracking-wider mb-2 block">
          Language
        </label>
        <select
          value={language}
          onChange={(e) => onLanguageChange(e.target.value)}
          className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:border-saffron"
        >
          {LANGUAGES.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>

      {/* Quick Navigation */}
      <div className="flex-1 px-4">
        <QuickNav />
      </div>

      {/* Session ID */}
      <div className="p-4 border-t border-border">
        <p className="text-xs text-ink-faint">Session: {sessionId.slice(-8)}</p>
      </div>
    </aside>
  );
}
