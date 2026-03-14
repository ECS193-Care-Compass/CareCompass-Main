import { useState, useRef, useEffect } from 'react'
import type { JSX } from 'react'
import { ArrowUp } from 'lucide-react'

interface Message {
  id: string
  text: string
  isUser: boolean
  timestamp: Date
}

const GUIDED_PROMPTS = [
  { label: 'Mental Health Support', scenario: 'mental_health' },
  { label: 'Practical Needs Help', scenario: 'practical_social' },
  { label: 'Legal & Advocacy Help', scenario: 'legal_advocacy' }
]

const INITIAL_GREETING =
  "Hello, you're safe here. I'm here to listen and provide support. How can I help you today?"

export function Chatbot(): JSX.Element {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [hasStarted, setHasStarted] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)

  // Suppress unused variable warning - keep for future quick exit feature
  void messagesEndRef

  const scrollToBottom = (): void => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const generateResponse = (userMessage: string): string => {
    const lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.includes('immediate') || lowerMessage.includes('emergency') || lowerMessage.includes('danger')) {
      return "Your safety is the priority. If you're in immediate danger, please call 911. The National Domestic Violence Hotline is available 24/7 at 1-800-799-7233. You can also text START to 88788. Would you like information about local safe spaces?";
    }
    
    if (lowerMessage.includes('options') || lowerMessage.includes('learn')) {
      return "I understand you want to explore your options. You have rights and there are resources available to you, including legal advocacy, safe housing, counseling services, and support groups. What area would you like to know more about?";
    }
    
    if (lowerMessage.includes('not sure') || lowerMessage.includes('start')) {
      return "It's completely okay to feel unsure. Taking this first step takes courage. We can talk about whatever feels right for you - your feelings, your situation, or practical next steps. There's no pressure. What feels most important to you right now?";
    }
    
    if (lowerMessage.includes('safe') || lowerMessage.includes('housing') || lowerMessage.includes('shelter')) {
      return "There are safe housing options available in Sacramento. WEAVE offers emergency shelter (916-920-2952) and My Sister's House provides transitional housing. These spaces are confidential and secure. Would you like more details about accessing these services?";
    }
    
    if (lowerMessage.includes('legal') || lowerMessage.includes('lawyer') || lowerMessage.includes('restraining order')) {
      return "Legal advocacy is available to help you understand your rights and options. This can include restraining orders, custody support, and immigration assistance. Organizations like Legal Services of Northern California offer free legal help. Would you like contact information?";
    }
    
    if (lowerMessage.includes('thank') || lowerMessage.includes('appreciate')) {
      return "You're welcome. Remember, you deserve support and safety. I'm here whenever you need to talk. You're taking important steps.";
    }
    
    return "I'm here to support you. Your feelings are valid, and you don't have to go through this alone. Would you like to talk more about your situation, or would information about specific resources be more helpful right now?";
  };

  const handleSendMessage = (messageText?: string) => {
    const textToSend = messageText || inputValue.trim();
    
    if (!textToSend) return;

    // Mark as started without adding greeting to messages
    if (!hasStarted) {
      setHasStarted(true);
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      text: textToSend,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    setTimeout(() => {
      const response = generateResponse(textToSend);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response,
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
    }, 800);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div 
      className={`flex flex-col h-[600px] bg-white rounded-lg transition-all ${
        isHovered ? 'border border-slate-200 shadow-sm' : 'border-0 shadow-none'
      }`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Messages Container or Initial Greeting */}
      {!hasStarted ? (
        <div className="flex-grow flex items-center justify-center px-6">
          <p className="text-center text-slate-600 max-w-md">
            {INITIAL_GREETING}
          </p>
        </div>
      ) : (
        <div 
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto px-6 py-4 space-y-4"
        >
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-4 py-3 ${
                  message.isUser
                    ? 'bg-slate-800 text-white'
                    : 'bg-slate-100 text-slate-800'
                }`}
              >
                <p className="text-sm leading-relaxed">{message.text}</p>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Guided Prompts - Always visible */}
      <div className="px-6 py-3 flex justify-center">
        <div className="flex flex-wrap gap-2 justify-center">
          {GUIDED_PROMPTS.map((prompt) => (
            <button
              key={prompt.scenario}
              onClick={() => handleSendMessage(prompt.label)}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-full text-sm transition-colors"
            >
              {prompt.label}
            </button>
          ))}
          
        </div>
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-slate-200">
        <div className="relative">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="w-full pl-4 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-slate-300 text-sm"
          />
          <button
            onClick={() => handleSendMessage()}
            disabled={!inputValue.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-slate-800 text-white rounded-full hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
            aria-label="Send message"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
