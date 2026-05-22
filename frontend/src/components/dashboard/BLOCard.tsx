import { User, Phone, Mail } from 'lucide-react';

interface BLOCardProps {
  bloName?: string;
  bloPhone?: string;
  bloEmail?: string;
}

export default function BLOCard({ bloName, bloPhone, bloEmail }: BLOCardProps) {
  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <div className="flex items-center gap-2 mb-4">
        <User className="w-4 h-4 text-saffron" />
        <h3 className="text-sm font-medium text-ink">Booth Level Officer (BLO)</h3>
      </div>

      <div className="space-y-3">
        {bloName && (
          <div>
            <p className="text-xs text-ink-faint">Name</p>
            <p className="text-sm text-ink">{bloName}</p>
          </div>
        )}
        {bloPhone && (
          <div className="flex items-center gap-2">
            <Phone className="w-4 h-4 text-ink-dim" />
            <a href={`tel:${bloPhone}`} className="text-sm text-saffron hover:text-saffron-warm">
              {bloPhone}
            </a>
          </div>
        )}
        {bloEmail && (
          <div className="flex items-center gap-2">
            <Mail className="w-4 h-4 text-ink-dim" />
            <a href={`mailto:${bloEmail}`} className="text-sm text-saffron hover:text-saffron-warm">
              {bloEmail}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
