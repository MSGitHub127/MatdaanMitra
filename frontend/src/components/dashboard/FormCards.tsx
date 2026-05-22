import { VoterProfile } from '../../types/voter';
import { ChevronDown, ChevronUp, Download } from 'lucide-react';
import { useState } from 'react';

interface FormCardsProps {
  profile: VoterProfile;
}

const FORMS = [
  {
    id: 'form6',
    name: 'Form 6',
    title: 'New Voter Registration',
    description: 'For first-time voters or those who have never been registered',
    applicable: ['new'],
  },
  {
    id: 'form8',
    name: 'Form 8',
    title: 'Address Correction',
    description: 'For voters who have moved within the same constituency',
    applicable: ['relocation', 'correction'],
  },
  {
    id: 'form6a',
    name: 'Form 6A',
    title: 'NRI Voter Registration',
    description: 'For overseas Indian citizens',
    applicable: ['nri'],
  },
];

export default function FormCards({ profile }: FormCardsProps) {
  const [expandedForm, setExpandedForm] = useState<string | null>(null);

  const relevantForms = FORMS.filter(
    (form) =>
      !profile.registration_type || form.applicable.includes(profile.registration_type)
  );

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-ink">Required Forms</h3>

      {relevantForms.map((form) => (
        <div
          key={form.id}
          className="bg-card rounded-lg border border-border overflow-hidden"
        >
          <button
            onClick={() =>
              setExpandedForm(expandedForm === form.id ? null : form.id)
            }
            className="w-full flex items-center justify-between p-4 text-left"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-ink">{form.name}</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-saffron/10 text-saffron">
                  {form.title}
                </span>
              </div>
              <p className="text-xs text-ink-dim mt-1">{form.description}</p>
            </div>
            {expandedForm === form.id ? (
              <ChevronUp className="w-4 h-4 text-ink-dim" />
            ) : (
              <ChevronDown className="w-4 h-4 text-ink-dim" />
            )}
          </button>

          {expandedForm === form.id && (
            <div className="px-4 pb-4 pt-0 border-t border-border">
              <div className="flex items-center gap-2 mt-3">
                <Download className="w-4 h-4 text-saffron" />
                <a
                  href={`https://eci.gov.in/files/file/${form.id.toLowerCase()}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-saffron hover:text-saffron-warm"
                >
                  Download {form.name} PDF
                </a>
              </div>
              <p className="text-xs text-ink-dim mt-2">
                Submit to your local ERO office or BLO
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
