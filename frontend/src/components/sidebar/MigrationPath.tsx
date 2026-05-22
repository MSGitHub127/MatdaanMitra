import { VoterProfile } from '../../types/voter';

interface MigrationPathProps {
  profile: VoterProfile;
}

export default function MigrationPath({ profile }: MigrationPathProps) {
  if (!profile.previous_state && !profile.previous_constituency) {
    return null;
  }

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <h2 className="text-sm font-medium text-ink mb-3">Migration Path</h2>

      <div className="space-y-3">
        {profile.previous_state && (
          <div className="flex items-start gap-2">
            <div className="w-2 h-2 rounded-full bg-ink-faint mt-1.5" />
            <div>
              <p className="text-xs text-ink-faint">Previous</p>
              <p className="text-sm text-ink">{profile.previous_state}</p>
              {profile.previous_constituency && (
                <p className="text-xs text-ink-dim">{profile.previous_constituency}</p>
              )}
            </div>
          </div>
        )}

        <div className="flex items-center justify-center">
          <div className="w-0.5 h-4 bg-border" />
        </div>

        {profile.current_state && (
          <div className="flex items-start gap-2">
            <div className="w-2 h-2 rounded-full bg-saffron mt-1.5" />
            <div>
              <p className="text-xs text-ink-faint">Current</p>
              <p className="text-sm text-ink">{profile.current_state}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
