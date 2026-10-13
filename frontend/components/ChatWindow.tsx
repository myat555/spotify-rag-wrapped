"use client";

import { useRef, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { streamChat } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "What genre did I listen to most this year?",
  "When during the day do I listen the most?",
  "Do I have a favorite artist streak?",
];

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  async function send(question: string) {
    if (!question.trim() || busy) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }, { role: "assistant", content: "" }]);
    setBusy(true);

    try {
      for await (const chunk of streamChat(question)) {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = {
            role: "assistant",
            content: next[next.length - 1].content + chunk,
          };
          return next;
        });
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      }
    } catch (e) {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = { role: "assistant", content: `Error: ${(e as Error).message}` };
        return next;
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex h-screen max-w-2xl flex-col px-6 py-6">
      <header className="mb-4 flex items-center justify-between">
        <Link href="/" className="text-sm text-[var(--text-secondary)] hover:text-white">
          &larr; Dashboard
        </Link>
        <h1 className="text-lg font-semibold">Ask your Wrapped</h1>
        <span className="w-16" />
      </header>

      <div className="flex-1 overflow-y-auto rounded-3xl border border-[var(--border-glass)] bg-[var(--surface-glass)] p-4 backdrop-blur-xl">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <p className="text-[var(--text-secondary)]">Ask anything about your listening history.</p>
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-[var(--border-glass)] px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-white"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-3">
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                m.role === "user" ? "self-end text-white" : "self-start bg-white/[0.06] text-[var(--text-primary)]"
              }`}
              style={m.role === "user" ? { background: "var(--accent-gradient)" } : undefined}
            >
              {m.content || (m.role === "assistant" && busy ? "..." : "")}
            </motion.div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="mt-4 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your vibe..."
          className="flex-1 rounded-full border border-[var(--border-glass)] bg-[var(--surface-glass)] px-5 py-3 text-sm outline-none placeholder:text-[var(--text-muted)]"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-full px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
          style={{ background: "var(--accent-gradient)" }}
        >
          Send
        </button>
      </form>
    </div>
  );
}
