export default function Header() {
  return (
    <header className="px-6 py-4 border-b border-border bg-surface">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold text-ink">Matdaan Mitra</h1>
          <p className="text-xs text-ink-dim">मतदान मित्र</p>
        </div>
        <div className="flex items-center gap-4">
          <a
            href="https://eci.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-ink-dim hover:text-ink transition-colors"
          >
            ECI Portal
          </a>
          <a
            href="https://nvsp.in"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-ink-dim hover:text-ink transition-colors"
          >
            NVSP
          </a>
        </div>
      </div>
    </header>
  );
}
