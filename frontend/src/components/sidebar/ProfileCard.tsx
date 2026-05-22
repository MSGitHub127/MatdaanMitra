import { VoterProfile } from '../../types/voter';
import { cn } from '../../lib/utils';

interface ProfileCardProps {
  profile: VoterProfile;
}

export default function ProfileCard({ profile }: ProfileCardProps) {
  const completionPercentage = profile.checklist
    ? Object.values(profile.checklist).filter(Boolean).length /
      Object.values(profile.checklist).length
    : 0;

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <h2 className="text-sm font-medium text-ink mb-3">Voter Profile</h2>

      <div className="space-y-2">
        {profile.name && (
          <div>
            <p className="text-xs text-ink-faint">Name</p>
            <p className="text-sm text-ink">{profile.name}</p>
          </div>
        )}

        {profile.current_state && (
          <div>
            <p className="text-xs text-ink-faint">State</p>
            <p className="text-sm text-ink">{profile.current_state}</p>
          </div>
        )}

        {profile.registration_type && (
          <div>
            <p className="text-xs text-ink-faint">Registration Type</p>
            <p className="text-sm text-ink capitalize">{profile.registration_type}</p>
          </div>
        )}
      </div>

      {/* Document Completeness Arc */}
      {profile.checklist && (
        <div className="mt-4 pt-4 border-t border-border">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-ink-faint">Documents Ready</p>
            <p className="text-xs text-ink">{Math.round(completionPercentage * 100)}%</p>
          </div>
          <div className="h-2 bg-surface rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full transition-all duration-500',
                completionPercentage >= 1
                  ? 'bg-emerald'
                  : completionPercentage >= 0.5
                  ? 'bg-amber'
                  : 'bg-rose'
              )}
              style={{ width: `${completionPercentage * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
