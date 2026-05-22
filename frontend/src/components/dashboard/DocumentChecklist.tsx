import { Check } from 'lucide-react';

interface DocumentChecklistProps {
  checklist: Record<string, boolean>;
  onUpdate: (checklist: Record<string, boolean>) => void;
}

const DOCUMENTS = [
  { id: 'aadhaar', name: 'Aadhaar Card', description: 'Proof of identity and address' },
  { id: 'passport', name: 'Passport', description: 'Alternative proof of identity' },
  { id: 'voter_id', name: 'Existing Voter ID', description: 'For address correction' },
  { id: 'ration_card', name: 'Ration Card', description: 'Proof of address' },
  { id: 'passport_photo', name: 'Passport Photo', description: 'Recent passport size photo' },
];

export default function DocumentChecklist({
  checklist,
  onUpdate,
}: DocumentChecklistProps) {
  const toggleDocument = (id: string) => {
    onUpdate({
      ...checklist,
      [id]: !checklist[id],
    });
  };

  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <h3 className="text-sm font-medium text-ink mb-4">Document Checklist</h3>

      <div className="space-y-2">
        {DOCUMENTS.map((doc) => (
          <button
            key={doc.id}
            onClick={() => toggleDocument(doc.id)}
            className="w-full flex items-start gap-3 p-3 rounded-lg border border-border hover:border-saffron/50 transition-colors text-left"
          >
            <div
              className={`w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 mt-0.5 ${
                checklist[doc.id]
                  ? 'bg-emerald border-emerald'
                  : 'border-border hover:border-saffron'
              }`}
            >
              {checklist[doc.id] && <Check className="w-3 h-3 text-bg" />}
            </div>
            <div>
              <p className="text-sm text-ink">{doc.name}</p>
              <p className="text-xs text-ink-dim">{doc.description}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
