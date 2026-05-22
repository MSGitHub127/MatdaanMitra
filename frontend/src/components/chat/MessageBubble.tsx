import { Message } from '../../types/voter';
import { cn, getConfidenceColor, getConfidenceLabel } from '../../lib/utils';
import ConfidenceRing from './ConfidenceRing';
import SourceDrawer from './SourceDrawer';
import { User, Bot } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isBot = message.role === 'bot';

  return (
    <div
      className={cn(
        'flex gap-3 animate-fade-slide-up',
        isBot ? 'justify-start' : 'justify-end'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
          isBot ? 'bg-saffron' : 'bg-sapphire'
        )}
      >
        {isBot ? (
          <Bot className="w-5 h-5 text-bg" />
        ) : (
          <User className="w-5 h-5 text-bg" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 max-w-2xl">
        <div
          className={cn(
            'rounded-lg p-4',
            isBot ? 'bg-card border border-border' : 'bg-sapphire/10'
          )}
        >
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-ink">
              {isBot ? 'Matdaan Mitra' : 'You'}
            </span>
            {isBot && message.confidence !== undefined && (
              <div className="flex items-center gap-1">
                <ConfidenceRing score={message.confidence} size={16} />
                <span className="text-xs text-ink-dim">
                  {getConfidenceLabel(message.confidence)}
                </span>
              </div>
            )}
          </div>

          {/* Text */}
          <p className="text-sm text-ink whitespace-pre-wrap">{message.text}</p>

          {/* Source Drawer */}
          {isBot && message.sourceChunks && message.sourceChunks.length > 0 && (
            <SourceDrawer chunks={message.sourceChunks} />
          )}
        </div>

        {/* Timestamp */}
        <p className="text-xs text-ink-faint mt-1">
          {new Date(message.timestamp).toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  );
}
