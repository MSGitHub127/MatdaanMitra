import { VoterProfile } from '../../types/voter';
import { FileText, Clock, CheckCircle, AlertTriangle } from 'lucide-react';

interface StatGridProps {
  profile: VoterProfile;
}

export default function StatGrid({ profile }: StatGridProps) {
  const completionPercentage = profile.checklist
    ? Math.round(
        (Object.values(profile.checklist).filter(Boolean).length /
          Object.values(profile.checklist).length) *
          100
      )
    : 0;

  const stats = [
    {
      icon: FileText,
      label: 'Forms',
      value: profile.registration_type ? '1 Active' : '0',
      color: 'text-sapphire',
    },
    {
      icon: Clock,
      label: 'Days Left',
      value: '30',
      color: 'text-amber',
    },
    {
      icon: CheckCircle,
      label: 'Documents',
      value: `${completionPercentage}%`,
      color: 'text-emerald',
    },
    {
      icon: AlertTriangle,
      label: 'Pending',
      value: profile.checklist
        ? Object.values(profile.checklist).filter((v) => !v).length
        : 0,
      color: 'text-rose',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-card rounded-lg p-4 border border-border"
        >
          <div className="flex items-center gap-2 mb-2">
            <stat.icon className={`w-4 h-4 ${stat.color}`} />
            <span className="text-xs text-ink-faint">{stat.label}</span>
          </div>
          <p className="text-2xl font-display font-semibold text-ink">
            {stat.value}
          </p>
        </div>
      ))}
    </div>
  );
}
