import { FileText, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import type { VoterProfile } from '../../types/voter';

interface StatGridProps {
  profile: VoterProfile;
}

// Phase 3 Maharashtra Assembly 2026 — registration deadline
const PHASE_DEADLINE = new Date('2026-09-30T23:59:59+05:30');

function getDaysLeft(): number {
  const now = new Date();
  const diff = Math.ceil((PHASE_DEADLINE.getTime() - now.getTime()) / 86_400_000);
  return Math.max(0, diff);
}

function getFormCount(type: VoterProfile['registration_type']): string {
  if (!type) return '—';
  const map: Record<string, number> = {
    new: 1, // Form 6
    relocation: 2, // Form 6 + Form 7
    correction: 1, // Form 8
    nri: 1, // Form 6A
  };
  const n = map[type] ?? 0;
  return `${n} required`;
}

export default function StatGrid({ profile }: StatGridProps) {
  const checklist = profile.checklist ?? {};
  const total = Object.keys(checklist).length;
  const done = Object.values(checklist).filter(Boolean).length;
  const pending = total - done;
  const completion = total > 0 ? Math.round((done / total) * 100) : 0;
  const daysLeft = getDaysLeft();

  const stats = [
    {
      icon: FileText,
      label: 'Forms',
      value: getFormCount(profile.registration_type),
      sub: profile.registration_type?.toUpperCase() ?? 'Not set',
      color: '#38BDF8',
      bgColor: 'var(--sapphire-dim)',
    },
    {
      icon: Clock,
      label: 'Days Left',
      value: daysLeft > 0 ? `${daysLeft}` : 'Deadline passed',
      sub: 'Phase 3 · Sep 30',
      color: daysLeft > 30 ? '#10B981' : daysLeft > 7 ? '#FBBF24' : '#FB7185',
      bgColor: daysLeft > 30 ? 'var(--emerald-dim)' : daysLeft > 7 ? 'var(--amber-dim)' : 'var(--rose-dim)',
    },
    {
      icon: CheckCircle,
      label: 'Documents',
      value: total > 0 ? `${completion}%` : '—',
      sub: total > 0 ? `${done} of ${total} ready` : 'Start checklist',
      color: completion >= 80 ? '#10B981' : completion >= 50 ? '#FBBF24' : '#F97316',
      bgColor: 'var(--emerald-dim)',
    },
    {
      icon: AlertTriangle,
      label: 'Pending',
      value: total > 0 ? `${pending}` : '—',
      sub: pending > 0 ? `${pending} document${pending !== 1 ? 's' : ''} missing` : 'All ready',
      color: pending > 0 ? '#FB7185' : '#10B981',
      bgColor: pending > 0 ? 'var(--rose-dim)' : 'var(--emerald-dim)',
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
      {stats.map(stat => (
        <div key={stat.label} style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 12, padding: '14px 14px 12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 8 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: stat.bgColor,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <stat.icon style={{ width: 14, height: 14, color: stat.color }} />
            </div>
            <span style={{ fontSize: 11, color: 'var(--ink-ghost)' }}>{stat.label}</span>
          </div>

          <p style={{
            fontFamily: 'Fraunces, Georgia, serif',
            fontSize: 22, fontWeight: 700, color: stat.color,
            lineHeight: 1, margin: '0 0 3px',
          }}>
            {stat.value}
          </p>
          <p style={{ fontSize: 10, color: 'var(--ink-ghost)', lineHeight: 1.3 }}>
            {stat.sub}
          </p>
        </div>
      ))}
    </div>
  );
}