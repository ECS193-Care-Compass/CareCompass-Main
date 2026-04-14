import { useEffect, useRef, useState } from "react"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import ReactMarkdown from "react-markdown"
import { ArrowUp, Mic } from "lucide-react"
import { motion, AnimatePresence } from 'framer-motion'
import { sendChatMessage, sendVoiceChat } from "../api"

interface WelcomeGlowBoxProps {
  sessionId: string
  authToken?: string
}

interface Message {
  role: "user" | "ai" | "error"
  text: string;
}

export const WelcomeGlowBox = ({ sessionId, authToken }: WelcomeGlowBoxProps) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const chatRef = useRef<HTMLDivElement | null>(null);
  const lastMsgRef = useRef<HTMLDivElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (chatRef.current) {
      // scroll after DOM update
      setTimeout(() => {
        if (chatRef.current) {
          chatRef.current.scrollTop = chatRef.current.scrollHeight
        }
      }, 50);
    }
  }, [messages])

  const sendMessage = async (override?: string) => {
    const text = (override ?? input).trim();
    if (!text || isLoading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    // scroll down shortly after adding
    setTimeout(() => {
      if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }, 20);
    setIsLoading(true);
    
    try {
      const data = await sendChatMessage(text, undefined, sessionId, authToken);
      setMessages((prev) => [...prev, { role: "ai", text: data.response }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "error", text: "Connection error." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        await handleVoiceSubmit(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "error", text: "Microphone access denied. Please check your browser permissions." },
      ]);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleVoiceSubmit = async (blob: Blob) => {
    setIsLoading(true);
    try {
      const data = await sendVoiceChat(blob, sessionId, authToken);

      setMessages((prev) => [
        ...prev,
        { role: "user", text: data.user_transcript },
        { role: "ai", text: data.bot_response },
      ]);

      if (data.audio_base64) {
        const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`);
        audio.play().catch((e) => console.error("Audio playback failed:", e));
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "error", text: "Sorry, I had trouble processing your voice message. Please try again or type your message." },
      ]);
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
    <div className="relative flex flex-col w-full max-w-[min(90vw,70rem)] mx-auto mt-0 px-4 sm:px-6 md:px-12 py-2 h-[80vh] sm:h-[75vh] md:h-[70vh] max-h-[calc(100vh-12rem)] transition-all duration-300 border border-transparent rounded-3xl hover:bg-transparent hover:border-teal-700/40">
      {/* REMOVE COMMENT TO ENABLE LANGUAGE BUTTON */}
      {/* {messages.length === 0 && (
        <div className="absolute top-4 right-6">
          <button
            onClick={() => setLanguage(language === 'en' ? 'es' : 'en')}
            className="flex items-center gap-1 px-4 py-1 bg-white/40 text-teal-900 rounded-full text-sm hover:bg-white/60 transition-colors"
          >
            <Globe className="w-4 h-4" />
            {language === 'en' ? 'ES' : 'EN'}
          </button>
        </div>
      )} */}
      {/* Message Area (flexible height, scrolls when overflowing) */}
      <div ref={chatRef} className="flex-1 w-full overflow-y-auto px-4 py-4 flex flex-col">
        <div className={`space-y-4 ${messages.length === 0 ? 'flex-1 flex items-center justify-center' : ''}`}>
            {messages.length === 0 ? (
              <h2 className="text-2xl font-medium text-center text-teal-900/80">
                Hello, you're safe here. I'm here to listen and provide support.
                <br />
                How can I help you today?
              </h2>
            ) : (
              <>
                {messages.map((m, i) => (
                  <motion.div
                    ref={i === messages.length - 1 ? lastMsgRef : null}
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div className={`max-w-[80%] p-3 rounded-lg text-sm ${m.role === "user" ? "bg-teal-700 text-white rounded-tr-none" : "bg-white/40 text-cyan-950 shadow-sm rounded-tl-none"}`}>
                      <ReactMarkdown>{m.text}</ReactMarkdown>
                    </div>
                  </motion.div>
                ))}
                {isLoading && <div className="text-xs text-cyan-800 animate-pulse">Thinking...</div>}
              </>
            )}
          </div>
        </div>


      {/* Guided Prompts (above input) or loading indicator when thinking */}
      <div className="flex flex-wrap justify-center gap-4 mt-2">
        <AnimatePresence mode="wait">
          {isLoading && (
            <motion.div
              key="loading-dots"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="flex items-center gap-1 text-teal-900"
            >
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="text-4xl"
                  animate={{
                    y: [0, -10, 0],
                  }}
                  transition={{
                    duration: 0.6,
                    repeat: Infinity,
                    delay: i * 0.15,
                    ease: "easeInOut"
                  }}
                >
                  •
                </motion.span>
              ))}
            </motion.div>
          )}
          {!isLoading && (
            <motion.div
              key="options"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="flex flex-wrap justify-center gap-4"
            >
              {GUIDED_PROMPTS.map((p) => (
                <Button
                  key={p.label}
                  variant="outline"
                  onClick={() => sendMessage(p.label)}
                  className="px-6 py-3 text-teal-900 border-teal-800/20 bg-white/40 rounded-2xl hover:bg-white/60 hover:border-teal-800/40"
                >
                  {p.label}
                </Button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Bar */}
      <div className="w-full mt-4 p-4 bg-transparent">
        <div className="relative flex items-center">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(); }}
            placeholder="How can I help you safely?"
            className="w-full bg-white/40 border-none rounded-xl py-4 md:py-5 pl-4 pr-20 text-sm focus:ring-2 focus:ring-teal-700/40"
          />
          <button
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            disabled={isLoading}
            className={`absolute right-12 p-1.5 rounded-full transition-all ${
              isRecording
                ? "bg-red-500 text-white animate-pulse scale-110"
                : "bg-teal-600 text-white hover:bg-teal-700"
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            aria-label="Hold to record voice message"
            title="Hold to talk"
          >
            <Mic size={18} className={isRecording ? "fill-current" : ""} />
          </button>
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
