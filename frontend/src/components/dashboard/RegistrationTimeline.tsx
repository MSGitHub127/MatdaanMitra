import { VoterProfile } from '../../types/voter';
import { Calendar } from 'lucide-react';

interface RegistrationTimelineProps {
  profile: VoterProfile;
}

export default function RegistrationTimeline({ profile }: RegistrationTimelineProps) {
  const milestones = [
    { label: 'Form Submission', date: '2026-05-15', status: 'pending' },
    { label: 'Document Verification', date: '2026-05-20', status: 'pending' },
    { label: 'BLO Verification', date: '2026-05-25', status: 'pending' },
    { label: 'Final Approval', date: '2026-06-01', status: 'pending' },
  ];

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <div className="flex items-center gap-2 mb-4">
        <Calendar className="w-4 h-4 text-saffron" />
        <h3 className="text-sm font-medium text-ink">Registration Timeline</h3>
      </div>

      <div className="space-y-3">
        {milestones.map((milestone, index) => (
          <div key={milestone.label} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={`w-3 h-3 rounded-full ${
                  milestone.status === 'completed'
                    ? 'bg-emerald'
                    : milestone.status === 'current'
                    ? 'bg-saffron animate-pulse'
                    : 'bg-border'
                }`}
              />
              {index < milestones.length - 1 && (
                <div className="w-0.5 flex-1 bg-border mt-1" />
              )}
            </div>
            <div className="flex-1 pb-3">
              <p className="text-sm text-ink">{milestone.label}</p>
              <p className="text-xs text-ink-dim">{milestone.date}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
