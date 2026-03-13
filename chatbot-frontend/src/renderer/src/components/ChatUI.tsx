import type { Message } from '../types/message'
import type { JSX } from 'react'
import ReactMarkdown from 'react-markdown'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowUp, Trash2 } from 'lucide-react'

interface ChatUIProps {
  messages: Message[]
  input: string
  isLoading: boolean
  scenario: string | null
  setInput: (value: string) => void
  setScenario: (value: string | null) => void
  handleSend: (overrideMessage?: string) => void
  handleClearChat: () => void
}

export default function ChatUI({
  messages,
  input,
  isLoading,
  scenario,
  setInput,
  setScenario,
  handleSend,
  handleClearChat
}: ChatUIProps): JSX.Element {
  return (
    <div className="flex flex-col h-[600px] bg-white/20 backdrop-blur-md rounded-3xl border border-white/30 shadow-xl overflow-hidden">
      
      {/* 1. Header with Scenarios & Clear Action */}
      <div className="p-4 border-b border-white/20 bg-white/10 flex justify-between items-center">
        <div className="flex gap-2">
          {['mental_health', 'legal_advocacy', 'practical_social'].map((id) => (
            <button
              key={id}
              onClick={() => setScenario(scenario === id ? null : id)}
              className={`px-3 py-1 rounded-full text-xs transition-all ${
                scenario === id ? 'bg-teal-700 text-white' : 'bg-white/40 text-cyan-900'
              }`}
            >
              {id.replace('_', ' ')}
            </button>
          ))}
        </div>
        <button onClick={handleClearChat} className="text-cyan-900/50 hover:text-red-500 transition-colors">
          <Trash2 size={18} />
        </button>
      </div>

      {/* 2. Message Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
        <AnimatePresence initial={false}>
          {messages.map((msg, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, scale: 0.9, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[85%] p-4 rounded-2xl text-sm ${
                msg.role === 'user' 
                  ? 'bg-teal-700 text-white rounded-tr-none' 
                  : 'bg-white text-cyan-950 rounded-tl-none shadow-sm'
              }`}>
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {isLoading && <div className="text-xs text-cyan-800 animate-pulse">Typing...</div>}
      </div>

      {/* 3. Input Bar */}
      <div className="p-4 bg-white/10 border-t border-white/20">
        <div className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="How can I help you safely?"
            className="w-full bg-white/90 border-none rounded-2xl py-3 pl-4 pr-12 text-sm focus:ring-2 focus:ring-teal-600"
          />
          <button 
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 p-1.5 bg-teal-700 text-white rounded-xl hover:bg-teal-800 disabled:opacity-30"
          >
            <ArrowUp size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}