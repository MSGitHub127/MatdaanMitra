/**
 * useChat.ts
 *
 * FIX: Empty bubble — missing 'replace' SSE event handler
 *
 * ROOT CAUSE (two-part):
 *
 *   1. synthesis.py used llm.ainvoke() without streaming=True on ChatVertexAI.
 *      This means no on_chat_model_stream events ever fired in LangGraph's
 *      astream_events loop. full_response stayed "" throughout generation.
 *      (Fixed in synthesis.py — see that file.)
 *
 *   2. When full_response is "" but result["final_response"] has content
 *      (the guardrail/translation wrote it), chat.py emits:
 *        data: {"type": "replace", "content": "...full answer..."}
 *      This is the correct fallback path for when the guardrail rewrites the
 *      streamed text, OR (as here) when streaming produced no tokens at all.
 *
 *      BUT: SSEToken in api.ts had no 'replace' type, so JSON.parse succeeded,
 *      the object was yielded, and useChat.ts fell into no branch — silently
 *      discarding the entire response. The bubble stayed empty.
 *
 * FIX:
 *   - Add 'replace' to the SSEToken union in api.ts (co-located here for clarity).
 *   - Handle token.type === 'replace' in useChat.ts by setting the full bubble
 *     text (not appending), replacing whatever partial text arrived via tokens.
 *
 * This makes the frontend robust to both streaming paths:
 *   Path A (Gemini streams): tokens arrive incrementally → bubble fills word by word.
 *   Path B (template fallback / guardrail rewrite): one 'replace' event → bubble
 *     fills instantly with the complete response.
 */

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
          // Incremental append — Gemini streaming path (streaming=True + astream())
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? { ...m, text: m.text + (token.content || '') }
                : m
            )
          );

        } else if (token.type === 'replace') {
          // FIX: Full replacement — fires when:
          //   (a) The guardrail rewrote the streamed text (political block, escalation)
          //   (b) The template fallback ran (no Vertex AI / GCP not configured) and
          //       no token events were emitted — full_response was "" in chat.py,
          //       so the entire response arrives here as a single replace event.
          // We SET (not append) the bubble text to the full replacement content.
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? { ...m, text: token.content || '' }
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