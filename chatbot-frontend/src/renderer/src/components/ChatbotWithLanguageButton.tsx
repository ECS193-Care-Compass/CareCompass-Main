import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { ArrowUp } from 'lucide-react';
import { motion } from 'framer-motion';

interface Message {
  role: 'user' | 'ai' | 'error';
  text: string;
}

export function ChatbotWithLanguageButton() {
  // --- LOGIC STATE ---
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', text: "Hello! I am CareCompass. I'm here to listen and provide support. How can I help you today?" }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [scenario, setScenario] = useState<string | null>(null);
  const [language, setLanguage] = useState<'en' | 'es'>('en');
  const scrollRef = useRef<HTMLDivElement>(null);

  // --- AUTO-SCROLL ---
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // --- API HANDLER ---
  const handleSend = async (overrideMessage?: string) => {
    const userMessage = (overrideMessage || input).trim();
    if (!userMessage || isLoading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMessage, scenario, lang: language }),
      });
      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'ai', text: data.response }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'error', text: 'Connection error. Please try again.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const categories = [
    { id: 'mental_health', label: 'Mental Health' },
    { id: 'practical_social', label: 'Practical Needs' },
    { id: 'legal_advocacy', label: 'Legal & Advocacy' },
  ];

  return (
    <div className="flex flex-col h-[650px] bg-white/20 backdrop-blur-md rounded-3xl border border-white/30 shadow-2xl overflow-hidden">
      
      {/* HEADER & LANGUAGE TOGGLE */}
      <div className="p-6 flex justify-between items-center bg-white/10 border-b border-white/20">
        <h2 className="text-xl font-bold text-cyan-900">CareCompass AI</h2>
        <button 
          onClick={() => setLanguage(language === 'en' ? 'es' : 'en')}
          className="px-3 py-1 text-xs rounded-full border border-cyan-800 text-cyan-900 hover:bg-cyan-800 hover:text-white transition-all"
        >
          {language === 'en' ? 'ESPAÑOL' : 'ENGLISH'}
        </button>
      </div>

      {/* CATEGORY CHIPS */}
      <div className="px-6 py-3 flex gap-2 flex-wrap bg-white/5">
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setScenario(scenario === cat.id ? null : cat.id)}
            className={`px-3 py-1.5 rounded-full text-xs transition-all ${
              scenario === cat.id ? 'bg-cyan-800 text-white' : 'bg-white/40 text-cyan-900 hover:bg-white/60'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* MESSAGES AREA */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg, idx) => (
          <motion.div 
            initial={{ opacity: 0, y: 10 }} 
            animate={{ opacity: 1, y: 0 }} 
            key={idx} 
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[80%] p-4 rounded-2xl text-sm shadow-sm ${
              msg.role === 'user' ? 'bg-teal-700 text-white rounded-tr-none' : 'bg-white text-cyan-950 rounded-tl-none'
            }`}>
              <ReactMarkdown>{msg.text}</ReactMarkdown>
            </div>
          </motion.div>
        ))}
        {isLoading && <div className="text-xs text-cyan-900/50 animate-pulse">CareCompass is typing...</div>}
      </div>

      {/* INPUT AREA */}
      <div className="p-6 bg-white/10 border-t border-white/20">
        <div className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type your message..."
            className="w-full bg-white/80 border-none rounded-2xl py-4 pl-5 pr-14 text-sm focus:ring-2 focus:ring-teal-600 outline-none"
          />
          <button 
            onClick={() => handleSend()}
            className="absolute right-2 p-2 bg-teal-700 text-white rounded-xl hover:bg-teal-800 transition-colors"
          >
            <ArrowUp size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}