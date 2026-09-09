"use client";

import { useState } from "react";
import { sendAssistantMessage } from "@/lib/api";
import type { AssistantChatResponse } from "@/lib/types";
import { Card } from "@/components/Card";
import { Badge } from "@/components/Badge";
import { AssistantToolResultCard } from "@/components/AssistantToolResultCard";

const EXAMPLE_PROMPTS = [
  "Who needs relief in the next 30 days?",
  "Who can replace John Smith?",
  "Can Ahmed Rahman replace John Smith?",
  "What happens if John Smith stays another 14 days?",
  "Which sites currently have staffing shortages?",
];

interface Message {
  role: "user" | "assistant";
  text: string;
  response?: AssistantChatResponse;
}

// A fixed id for this browser tab's conversation - the backend keeps
// history in memory per id, so reusing the same one lets the manager
// ask a follow-up ("what about Diego instead?") with context intact.
const CONVERSATION_ID = `conv-${Math.random().toString(36).slice(2)}`;

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);
    try {
      const response = await sendAssistantMessage(text, CONVERSATION_ID);
      setMessages((prev) => [...prev, { role: "assistant", text: response.answer, response }]);
    } catch (err) {
      const message = String((err as Error).message ?? err);
      if (message.startsWith("503")) {
        setError(
          "The AI assistant isn't configured in this environment (no LLM_API_KEY is set). Every other Kinvera feature works normally without it."
        );
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Kinvera Assistant</h1>
        <p className="text-sm text-muted">
          Ask about workforce data in plain language. The assistant explains results computed by Kinvera&apos;s
          deterministic rules - it never decides eligibility, staffing, or simulation outcomes itself.
        </p>
      </div>

      <Card>
        <div className="flex min-h-[420px] flex-col gap-4">
          {messages.length === 0 && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Try asking</p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => send(prompt)}
                    className="rounded-full border border-border bg-gray-50 px-3 py-1.5 text-xs text-foreground hover:bg-gray-100"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
            {messages.map((message, idx) => (
              <div key={idx} className={message.role === "user" ? "self-end text-right" : "self-start"}>
                <div
                  className={
                    message.role === "user"
                      ? "inline-block rounded-lg bg-accent px-4 py-2 text-sm text-accent-foreground"
                      : "inline-block rounded-lg border border-border bg-surface px-4 py-2 text-sm text-foreground"
                  }
                >
                  {message.text}
                </div>

                {message.response && message.response.sources.length > 0 && (
                  <div className="mt-2 flex flex-col gap-3 text-left">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-xs text-muted">Based on:</span>
                      {message.response.sources.map((source) => (
                        <Badge key={source} tone="info">
                          {source.replace(/_/g, " ")}
                        </Badge>
                      ))}
                    </div>
                    {message.response.tool_results.map((tr, trIdx) => (
                      <AssistantToolResultCard key={trIdx} tool={tr.tool} result={tr.result} />
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && <p className="text-sm text-muted">Thinking...</p>}
            {error && (
              <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex gap-2 border-t border-border pt-4"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about workforce data..."
              className="flex-1 rounded-md border border-border px-3 py-2 text-sm outline-none focus:border-accent"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground disabled:opacity-60"
            >
              Send
            </button>
          </form>
        </div>
      </Card>
    </div>
  );
}
