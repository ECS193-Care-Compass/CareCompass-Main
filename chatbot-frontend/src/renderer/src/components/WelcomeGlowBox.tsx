import { useEffect, useRef, useState } from "react"
import { Button } from "./ui/button"
import { Input } from "./ui/input"

import ReactMarkdown from "react-markdown"
import { ArrowUp } from "lucide-react"

interface Message {
  role: "user" | "ai" | "error"
  text: string;
}

export const WelcomeGlowBox = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const chatRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
  }, [messages])

  const sendMessage = async (override?: string) => {
    const text = (override ?? input).trim();
    if (!text || isLoading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "ai", text: data.response }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "error", text: "Connection error." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const GUIDED_PROMPTS = [
    { label: "Mental Health Support", scenario: "mental_health" },
    { label: "Practical Needs Help", scenario: "practical_social" },
    { label: "Legal & Advocacy Help", scenario: "legal_advocacy" },
  ];

  return (
    <div className="flex flex-col w-full max-w-5xl mx-5 sm:mx-9 md:mx-auto px-4 sm:px-6 md:px-12 py-2 transition-all duration-300 border border-transparent rounded-3xl hover:bg-transparent hover:border-teal-700/40 group min-h-fit">
      {/* Message Area (always same height, greeting shown inside when empty) */}
      <div className="flex-1 w-full">
        <div ref={chatRef} className="h-[56vh] md:h-[500px] overflow-y-auto px-4 py-4">
          <div className="space-y-4 h-full">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <h2 className="text-2xl font-medium text-center text-teal-900/80">
                  Hello, you're safe here. I'm here to listen and provide support.
                  <br />
                  How can I help you today?
                </h2>
              </div>
            ) : (
              <>
                {messages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] p-3 rounded-lg text-sm ${m.role === "user" ? "bg-teal-700 text-white rounded-tr-none" : "bg-white text-cyan-950 shadow-sm rounded-tl-none"}`}>
                      <ReactMarkdown>{m.text}</ReactMarkdown>
                    </div>
                  </div>
                ))}
                {isLoading && <div className="text-xs text-cyan-800 animate-pulse">Thinking...</div>}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Guided Prompts (above input) */}
      <div className="flex flex-wrap justify-center gap-4 mt-4">
        {GUIDED_PROMPTS.map((p) => (
          <Button
            key={p.label}
            variant="outline"
            onClick={() => sendMessage(p.scenario)}
            className="px-6 py-3 text-teal-900 border-teal-800/20 bg-white/40 rounded-2xl hover:bg-white/60 hover:border-teal-800/40"
          >
            {p.label}
          </Button>
        ))}
      </div>

      {/* Input Bar */}
      <div className="w-full mt-4 p-4 bg-transparent">
        <div className="relative flex items-center">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(); }}
            placeholder="How can I help you safely?"
            className="w-full bg-white/90 border-none rounded-xl py-4 md:py-5 pl-4 pr-12 text-sm focus:ring-2 focus:ring-teal-700/40"
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 p-1.5 bg-teal-600 text-white rounded-full hover:bg-teal-700 disabled:bg-teal-600/50 disabled:text-white/70"
          >
            <ArrowUp size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};
