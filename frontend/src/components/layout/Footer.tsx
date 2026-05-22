export default function Footer() {
  return (
    <footer className="px-6 py-4 border-t border-border bg-surface">
      <div className="flex items-center justify-between text-xs text-ink-dim">
        <p>© 2026 Matdaan Mitra. All rights reserved.</p>
        <div className="flex items-center gap-4">
          <a
            href="https://eci.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-ink transition-colors"
          >
            ECI
          </a>
          <a
            href="https://nvsp.in"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-ink transition-colors"
          >
            NVSP
          </a>
          <a
            href="tel:1950"
            className="hover:text-ink transition-colors"
          >
            1950
          </a>
        </div>
      </div>
    </footer>
  );
}
