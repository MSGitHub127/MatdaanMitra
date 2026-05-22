import { useState, useCallback } from 'react';
import { streamChat } from '../lib/api';
import type { Message } from '../types/voter';

export function useChat(sessionId: string, language: string = 'en') {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    // Add user message immediately
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      text: text.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Prepare bot message placeholder
    const botMsgId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      {
        id: botMsgId,
        role: 'bot',
        text: '',
        timestamp: new Date(),
        isStreaming: true,
      },
    ]);

    setIsLoading(true);
    setError(null);

    try {
      for await (const token of streamChat(sessionId, text, language)) {
        if (token.type === 'token') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? { ...m, text: m.text + (token.content || '') }
                : m
            )
          );
        } else if (token.type === 'done') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? {
                    ...m,
                    isStreaming: false,
                    confidence: token.confidence,
                    sourceChunks: token.source_chunks,
                    agentTrace: token.agent_trace,
                  }
                : m
            )
          );
        } else if (token.type === 'error') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? {
                    ...m,
                    text: `Connection error: ${token.error}. Please try again.`,
                    isStreaming: false,
                  }
                : m
            )
          );
          setError(token.error || 'Connection failed');
        }
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Connection failed';
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMsgId
            ? { ...m, text: `Connection error: ${errMsg}. Please try again.`, isStreaming: false }
            : m
        )
      );
      setError(errMsg);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, language, isLoading]);

  return { messages, sendMessage, isLoading, error };
}
