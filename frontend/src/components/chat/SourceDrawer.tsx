import { RetrievedChunk } from '../../types/voter';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { useState } from 'react';

interface SourceDrawerProps {
  chunks: RetrievedChunk[];
}

export default function SourceDrawer({ chunks }: SourceDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-3 pt-3 border-t border-border">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-xs text-ink-dim hover:text-ink transition-colors"
      >
        {isOpen ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
        <span>Sources ({chunks.length})</span>
      </button>

      {isOpen && (
        <div className="mt-2 space-y-2">
          {chunks.map((chunk) => (
            <div
              key={chunk.chunk_id}
              className="bg-surface rounded p-2 text-xs"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-ink-dim">{chunk.form_type}</span>
                <span className="text-ink-faint">
                  {Math.round(chunk.confidence * 100)}%
                </span>
              </div>
              <p className="text-ink line-clamp-2 mb-1">{chunk.text}</p>
              {chunk.source_url && (
                <a
                  href={chunk.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-saffron hover:text-saffron-warm"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span>View Source</span>
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
