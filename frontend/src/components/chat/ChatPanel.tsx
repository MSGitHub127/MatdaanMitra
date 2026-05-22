import { Message } from '../../types/voter';
import MessageBubble from './MessageBubble';
import Composer from './Composer';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  language: string;
}

export default function ChatPanel({
  messages,
  onSendMessage,
  isLoading,
  language,
}: ChatPanelProps) {
  return (
    <div className="flex-1 flex flex-col bg-bg">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-border bg-surface">
        <h2 className="text-lg font-medium text-ink">Conversation</h2>
        <p className="text-sm text-ink-dim">Ask about voter registration, forms, deadlines</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-ink text-lg mb-2">Welcome to Matdaan Mitra</p>
              <p className="text-ink-dim text-sm">
                Ask me anything about voter registration, forms, or deadlines
              </p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
      </div>

      {/* Composer */}
      <div className="px-6 py-4 border-t border-border bg-surface">
        <Composer onSend={onSendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}
