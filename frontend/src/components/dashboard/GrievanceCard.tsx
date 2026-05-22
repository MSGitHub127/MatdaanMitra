import { AlertTriangle, FileText, ExternalLink } from 'lucide-react';

export default function GrievanceCard() {
  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-amber" />
        <h3 className="text-sm font-medium text-ink">File a Grievance</h3>
      </div>

      <div className="space-y-3">
        <p className="text-xs text-ink-dim">
          If your name is missing from the voter list or you have other issues,
          you can file a grievance with the Election Commission.
        </p>

        <div className="flex gap-2">
          <a
            href="https://eci.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2 bg-surface rounded-lg text-sm text-ink hover:bg-border transition-colors"
          >
            <FileText className="w-4 h-4" />
            <span>File Online</span>
          </a>
          <a
            href="https://eci.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2 bg-surface rounded-lg text-sm text-ink hover:bg-border transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Visit ECI</span>
          </a>
        </div>

        <p className="text-xs text-ink-faint">
          National Voter Helpline: 1950
        </p>
      </div>
    </div>
  );
}
