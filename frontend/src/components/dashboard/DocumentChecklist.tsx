'use client';

import { Check, Star } from 'lucide-react';
import type { VoterProfile, RegistrationType } from '../../types/voter';

interface DocumentChecklistProps {
  checklist: Record<string, boolean>;
  onUpdate: (checklist: Record<string, boolean>) => void;
  profile?: VoterProfile;
}

interface Document {
  id: string;
  name: string;
  description: string;
  required: boolean;
  note?: string;
}

// ── Document sets per registration type ──────────────────────────────────────

const DOCS_BY_TYPE: Record<string, Document[]> = {
  new: [
    { id: 'passport_photo', name: 'Passport Size Photo', description: '35mm × 45mm, recent, white background', required: true },
    { id: 'aadhaar', name: 'Aadhaar Card', description: 'Proof of identity + age', required: true },
    {
      id: 'birth_cert', name: 'Birth Certificate', description: 'Alternative age proof if DOB not on Aadhaar', required: false, note: 'If Aadhaar doesn\'t show DOB'
    },
    { id: 'address_proof', name: 'Address Proof', description: 'Utility bill / bank passbook (≤ 1 year)', required: true, note: 'If address differs from Aadhaar' },
    { id: 'declaration', name: 'Self-Declaration Form', description: 'Printed and signed Form 6 declaration', required: true },
  ],
  relocation: [
    { id: 'passport_photo', name: 'Passport Size Photo', description: '35mm × 45mm, recent, white background', required: true },
    { id: 'aadhaar', name: 'Aadhaar Card', description: 'Identity proof', required: true },
    { id: 'new_address', name: 'New Address Proof', description: 'Utility bill / rent agreement at new address (≤ 1 year)', required: true },
    { id: 'old_epic', name: 'Old EPIC Card (copy)', description: 'Existing voter ID from old constituency', required: false, note: 'For Form 7 deletion request' },
    { id: 'declaration', name: 'Self-Declaration Form', description: 'Printed and signed Form 6 / Form 7 declaration', required: true },
  ],
  correction: [
    { id: 'passport_photo', name: 'Passport Size Photo', description: '35mm × 45mm, recent, white background', required: true },
    { id: 'aadhaar', name: 'Aadhaar Card', description: 'Current identity proof', required: true },
    { id: 'correction_doc', name: 'Correction Document', description: 'Document proving the correct details (e.g., birth cert for DOB)', required: true },
    { id: 'old_epic', name: 'Existing EPIC Card', description: 'Current voter ID showing the incorrect detail', required: true },
  ],
  nri: [
    { id: 'passport_photo', name: 'Passport Size Photo', description: '35mm × 45mm, recent, white background', required: true },
    { id: 'passport', name: 'Indian Passport', description: 'Valid Indian passport (copy of biographical + address pages)', required: true },
    { id: 'visa', name: 'Visa / Entry Stamp', description: 'Current visa or entry stamp showing overseas residence', required: false, note: 'Recommended' },
    { id: 'declaration', name: 'NRI Declaration', description: 'Printed and signed Form 6A declaration', required: true },
  ],
};

const DEFAULT_DOCS: Document[] = [
  { id: 'passport_photo', name: 'Passport Size Photo', description: '35mm × 45mm, recent, white background', required: true },
  { id: 'aadhaar', name: 'Aadhaar Card', description: 'Primary proof of identity and address', required: true },
  { id: 'address_proof', name: 'Address Proof', description: 'Utility bill or bank passbook (≤ 1 year)', required: false },
  { id: 'pan_card', name: 'PAN Card', description: 'Alternative identity proof', required: false },
  { id: 'declaration', name: 'Self-Declaration Form', description: 'Signed form declaration', required: true },
];

export default function DocumentChecklist({
  checklist, onUpdate, profile,
}: DocumentChecklistProps) {
  const regType = profile?.registration_type;
  const docs = DOCS_BY_TYPE[regType ?? ''] ?? DEFAULT_DOCS;

  const totalRequired = docs.filter(d => d.required).length;
  const doneRequired = docs.filter(d => d.required && checklist[d.id]).length;
  const pct = totalRequired > 0 ? Math.round((doneRequired / totalRequired) * 100) : 0;

  const toggle = (id: string) => {
    onUpdate({ ...checklist, [id]: !checklist[id] });
  };

  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid var(--border)',
      borderRadius: 14, padding: 18,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <h3 style={{
            fontFamily: 'Fraunces, Georgia, serif',
            fontSize: 15, fontWeight: 700, color: 'var(--ink)', margin: '0 0 3px',
          }}>
            Document Checklist
          </h3>
          <p style={{ fontSize: 11, color: 'var(--ink-dim)' }}>
            {regType
              ? `Documents for ${regType.toUpperCase()} registration`
              : 'General documents — specify your type in chat for a personalised list'}
          </p>
        </div>
        <div style={{
          fontSize: 13, fontWeight: 700,
          color: pct === 100 ? 'var(--emerald)' : 'var(--saffron)',
        }}>
          {pct}%
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 4, background: 'var(--border)', borderRadius: 2, overflow: 'hidden', marginBottom: 16 }}>
        <div style={{
          height: '100%', width: `${pct}%`,
          background: pct === 100
            ? 'var(--emerald)'
            : 'linear-gradient(90deg, var(--saffron), var(--saffron-warm))',
          borderRadius: 2, transition: 'width .5s cubic-bezier(.34,1.56,.64,1)',
        }} />
      </div>

      {/* Document rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {docs.map(doc => {
          const checked = Boolean(checklist[doc.id]);
          return (
            <button
              key={doc.id}
              onClick={() => toggle(doc.id)}
              style={{
                all: 'unset', cursor: 'pointer',
                display: 'flex', alignItems: 'flex-start', gap: 11,
                padding: '11px 12px', borderRadius: 10,
                background: checked ? 'var(--emerald-dim)' : 'var(--surface)',
                border: `1px solid ${checked ? 'rgba(16,185,129,0.35)' : 'var(--border)'}`,
                transition: 'all .15s',
              }}
            >
              {/* Checkbox */}
              <div style={{
                width: 20, height: 20, borderRadius: 6, flexShrink: 0, marginTop: 1,
                border: `2px solid ${checked ? 'var(--emerald)' : 'var(--ink-ghost)'}`,
                background: checked ? 'var(--emerald)' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all .15s',
              }}>
                {checked && <Check style={{ width: 11, height: 11, color: '#030508', strokeWidth: 3 }} />}
              </div>

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{
                    fontSize: 13, fontWeight: 500,
                    color: checked ? 'var(--ink)' : 'var(--ink)',
                    textDecoration: checked ? 'line-through' : 'none',
                    textDecorationColor: 'var(--ink-ghost)',
                  }}>
                    {doc.name}
                  </span>
                  {doc.required && (
                    <span style={{
                      fontSize: 9, fontWeight: 700, letterSpacing: '.06em',
                      color: 'var(--saffron)',
                      background: 'var(--saffron-dim)',
                      border: '1px solid rgba(249,115,22,0.3)',
                      borderRadius: 4, padding: '1px 6px',
                    }}>
                      REQUIRED
                    </span>
                  )}
                </div>
                <p style={{ fontSize: 11, color: 'var(--ink-ghost)', marginTop: 2, lineHeight: 1.4 }}>
                  {doc.description}
                </p>
                {doc.note && (
                  <p style={{ fontSize: 10, color: 'var(--amber)', marginTop: 2 }}>
                    ℹ️ {doc.note}
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Completion message */}
      {pct === 100 && (
        <div style={{
          marginTop: 14, padding: '10px 13px',
          background: 'var(--emerald-dim)',
          border: '1px solid rgba(16,185,129,0.35)',
          borderRadius: 10, fontSize: 12, color: 'var(--emerald)',
          display: 'flex', alignItems: 'center', gap: 7,
        }}>
          ✅ All required documents ready — you can proceed to form submission!
        </div>
      )}
    </div>
  );
}