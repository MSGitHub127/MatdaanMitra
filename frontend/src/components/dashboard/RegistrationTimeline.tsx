'use client';

import { useMemo } from 'react';
import type { VoterProfile } from '../../types/voter';

interface RegistrationTimelineProps {
  profile: VoterProfile;
}

type MilestoneStatus = 'completed' | 'current' | 'pending' | 'blocked';

interface Milestone {
  icon: string;
  label: string;
  description: string;
  date: string;
  status: MilestoneStatus;
}

function deriveMilestones(profile: VoterProfile): Milestone[] {
  const checklist = profile.checklist ?? {};
  const totalDocs = Object.keys(checklist).length;
  const doneDocs = Object.values(checklist).filter(Boolean).length;
  const allDocsDone = totalDocs > 0 && doneDocs === totalDocs;
  const anyDocsDone = doneDocs > 0;
  const hasType = Boolean(profile.registration_type);
  const hasEPIC = Boolean(profile.epic_number);

  // Determine form name from registration type
  const formName = {
    new: 'Form 6',
    relocation: 'Form 6 + Form 7',
    correction: 'Form 8',
    nri: 'Form 6A',
    '': 'Registration Form' // Explicitly handle the default case here
  }[profile.registration_type ?? ''] || 'Registration Form';

  return [
    {
      icon: '🗂️',
      label: `${formName} Submitted`,
      description: hasType
        ? `Application type: ${profile.registration_type?.toUpperCase()}`
        : 'Tell the assistant your registration type to begin',
      date: profile.registered_at
        ? new Date(profile.registered_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
        : hasType ? 'Ready to submit' : 'Pending',
      status: hasType ? 'completed' : 'current',
    },
    {
      icon: '📄',
      label: 'Documents Collected',
      description: allDocsDone
        ? `All ${totalDocs} documents ready`
        : anyDocsDone
          ? `${doneDocs} of ${totalDocs} documents checked`
          : 'Open the Documents tab to track your documents',
      date: allDocsDone ? 'Complete' : 'In progress',
      status: allDocsDone ? 'completed' : hasType ? 'current' : 'blocked',
    },
    {
      icon: '🧑‍💼',
      label: 'BLO Home Verification',
      description: 'Booth Level Officer visits your address to confirm residence',
      date: 'Within 30 days of submission',
      status: allDocsDone ? 'current' : 'pending',
    },
    {
      icon: '🏛️',
      label: 'ERO Approval',
      description: 'Electoral Registration Officer reviews and approves your application',
      date: 'After BLO report',
      status: 'pending',
    },
    {
      icon: '🪪',
      label: 'EPIC Card Issued',
      description: hasEPIC
        ? `EPIC: ${profile.epic_number}`
        : 'Voter ID card will be dispatched to your address',
      date: hasEPIC ? 'Issued' : 'Within 45–60 days of approval',
      status: hasEPIC ? 'completed' : 'pending',
    },
  ];
}

const STATUS_STYLES: Record<MilestoneStatus, { dot: string; line: string; label: string }> = {
  completed: { dot: '#10B981', line: 'rgba(16,185,129,0.4)', label: 'var(--emerald)' },
  current: { dot: '#F97316', line: 'rgba(249,115,22,0.25)', label: 'var(--saffron)' },
  pending: { dot: '#3A5470', line: 'rgba(58,84,112,0.3)', label: 'var(--ink-ghost)' },
  blocked: { dot: '#1E3550', line: 'rgba(30,53,80,0.3)', label: 'var(--ink-ghost)' },
};

export default function RegistrationTimeline({ profile }: RegistrationTimelineProps) {
  const milestones = useMemo(() => deriveMilestones(profile), [profile]);

  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid var(--border)',
      borderRadius: 14, padding: 20,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 9,
          background: 'var(--saffron-dim)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16,
        }}>📅</div>
        <div>
          <h3 style={{
            fontFamily: 'Fraunces, Georgia, serif',
            fontSize: 15, fontWeight: 700, color: 'var(--ink)', margin: 0,
          }}>
            Registration Timeline
          </h3>
          <p style={{ fontSize: 11, color: 'var(--ink-dim)', marginTop: 2 }}>
            {profile.registration_type
              ? `${profile.registration_type.toUpperCase()} registration · ${profile.current_state ?? 'India'}`
              : 'Share your details in chat to personalise this timeline'}
          </p>
        </div>
      </div>

      {/* Milestones */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {milestones.map((m, i) => {
          const s = STATUS_STYLES[m.status];
          const isLast = i === milestones.length - 1;
          return (
            <div key={m.label} style={{ display: 'flex', gap: 14 }}>

              {/* Dot + connector */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                  background: m.status === 'completed'
                    ? 'var(--emerald-dim)'
                    : m.status === 'current'
                      ? 'var(--saffron-dim)'
                      : 'var(--surface)',
                  border: `2px solid ${s.dot}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13,
                  animation: m.status === 'current' ? 'pulse 2s ease infinite' : 'none',
                }}>
                  {m.status === 'completed' ? '✓' : m.icon}
                </div>
                {!isLast && (
                  <div style={{
                    width: 2, flex: 1, minHeight: 24,
                    background: s.line, margin: '4px 0',
                  }} />
                )}
              </div>

              {/* Content */}
              <div style={{ flex: 1, paddingBottom: isLast ? 0 : 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: 4 }}>
                  <span style={{
                    fontSize: 13, fontWeight: 600,
                    color: m.status === 'pending' || m.status === 'blocked'
                      ? 'var(--ink-dim)' : 'var(--ink)',
                  }}>
                    {m.label}
                  </span>
                  <span style={{
                    fontSize: 10, color: s.label,
                    fontWeight: m.status === 'completed' || m.status === 'current' ? 700 : 400,
                    flexShrink: 0, marginLeft: 8,
                  }}>
                    {m.status === 'completed' ? '✓ Done' : m.date}
                  </span>
                </div>
                <p style={{ fontSize: 11, color: 'var(--ink-ghost)', marginTop: 3, lineHeight: 1.5 }}>
                  {m.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}