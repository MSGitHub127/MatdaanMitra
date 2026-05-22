import { VoterProfile } from '../../types/voter';
import StatGrid from './StatGrid';
import RegistrationTimeline from './RegistrationTimeline';
import DocumentChecklist from './DocumentChecklist';
import FormCards from './FormCards';
import EROLocator from './EROLocator';

interface VoterDashboardProps {
  profile: VoterProfile;
  onUpdateChecklist: (checklist: Record<string, boolean>) => void;
}

export default function VoterDashboard({ profile, onUpdateChecklist }: VoterDashboardProps) {
  return (
    <div className="flex-1 bg-surface border-l border-border flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border">
        <h2 className="text-lg font-medium text-ink">Voter Dashboard</h2>
        <p className="text-sm text-ink-dim">Track your registration progress</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {/* Stat Grid */}
        <StatGrid profile={profile} />

        {/* Registration Timeline */}
        <RegistrationTimeline profile={profile} />

        {/* Document Checklist */}
        <DocumentChecklist
          checklist={profile.checklist || {}}
          onUpdate={onUpdateChecklist}
        />

        {/* Form Cards */}
        <FormCards profile={profile} />

        {/* ERO Locator */}
        <EROLocator />
      </div>
    </div>
  );
}
