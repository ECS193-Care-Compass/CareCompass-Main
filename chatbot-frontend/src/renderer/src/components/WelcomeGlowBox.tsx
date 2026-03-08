import { useEffect, useRef, useState } from "react"
import { Input } from "./ui/input"
import ReactMarkdown from "react-markdown"
import { ArrowUp, LogOut as LogOutIcon } from "lucide-react"
import { sendChatMessage } from "../api"

interface Message {
  role: "user" | "ai" | "error"
  text: string;
}

interface WelcomeGlowBoxProps {
  sessionId: string
  authToken?: string
  isGuest: boolean
  userEmail?: string
  onSignOut?: () => void
}

export const WelcomeGlowBox = ({ sessionId, authToken, isGuest, userEmail, onSignOut }: WelcomeGlowBoxProps) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const chatRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const query = (text ?? input).trim();
    if (!query || isLoading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: query }]);
    setIsLoading(true);

    try {
      const data = await sendChatMessage(query, undefined, sessionId, authToken);
      setMessages((prev) => [...prev, { role: "ai", text: data.response }]);
    } catch {
      setMessages((prev) => [...prev, { role: "error", text: "Connection error. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const GUIDED_PROMPTS = [
    "I need mental health support",
    "Help with practical needs",
    "Legal and advocacy information",
  ];

  return (
    <div className="flex flex-col w-full max-w-5xl mx-5 sm:mx-9 md:mx-auto px-4 sm:px-6 md:px-12 py-2 transition-all duration-300 border border-teal-700/20 rounded-3xl bg-white/5 hover:bg-white/10 hover:border-teal-700/40 group min-h-fit">
      {/* Session Info Bar */}
      <div className="flex items-center justify-between px-4 pt-3 pb-1">
        <span className="text-xs text-teal-800/50">
          {isGuest ? 'Guest session' : userEmail}
        </span>
        {!isGuest && onSignOut && (
          <button
            onClick={onSignOut}
            className="flex items-center gap-1 text-xs text-teal-800/50 hover:text-teal-900 transition-colors"
          >
            <LogOutIcon size={12} />
            Sign out
          </button>
        )}
      </div>

      {/* Message Area */}
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
                    <div className={`max-w-[80%] p-3 rounded-lg text-sm ${m.role === "user" ? "bg-teal-700 text-white" : m.role === "error" ? "bg-red-100/70 text-red-900" : "bg-white text-teal-950 shadow-sm"}`}>
                      <ReactMarkdown>{m.text}</ReactMarkdown>
                    </div>
                  </div>
                ))}
                {isLoading && <div className="text-xs text-teal-700/70 animate-pulse">Thinking...</div>}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Guided Prompts */}
      <div className="flex flex-wrap justify-center gap-3 mt-4">
        {GUIDED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => sendMessage(prompt)}
            disabled={isLoading}
            className="px-5 py-2 text-sm text-teal-900 border border-teal-700/30 bg-white/30 rounded-2xl hover:bg-white/50 hover:border-teal-700/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <div className="w-full mt-4 p-4 bg-transparent">
        <div className="relative flex items-center">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendMessage();
            }}
            placeholder="How can I help you safely?"
            className="w-full bg-white/80 border-teal-700/20 text-teal-950 placeholder-teal-700/60 rounded-xl py-3 md:py-4 pl-4 pr-12 text-sm focus:ring-2 focus:ring-teal-700/40 focus:border-transparent"
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 p-2 bg-teal-600 text-white rounded-full hover:bg-teal-700 transition-colors disabled:bg-teal-600/50 disabled:text-white/70"
          >
            <ArrowUp size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};
