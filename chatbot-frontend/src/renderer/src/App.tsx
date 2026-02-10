import { useState, useEffect, useMemo, useRef } from 'react'
import { sendChatMessage } from './api'

interface Message {
  role: 'user' | 'ai' | 'error';
  text: string;
}

function App(): React.JSX.Element {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', text: 'Hello! I am CareCompass. How can I help you today?' }
  ])
  const [isLoading, setIsLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const sessionId = useMemo(() => {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return `session-${crypto.randomUUID()}`
    }
    return `session-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
  }, [])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight)
  }, [messages])

  const handleSend = async (): Promise<void> => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }])
    setIsLoading(true)

    try {
      const data = await sendChatMessage(userMessage, sessionId, { anonymous: true })
      setMessages((prev) => [...prev, { role: 'ai', text: data.reply || 'No reply returned.' }])
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'error', text: 'Failed to connect to backend.' }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container" style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '20px' }}>
      <header>
        <h2 className="text">CareCompass AI</h2>
      </header>

      {/* Message Display Area */}
      <div 
        ref={scrollRef}
        style={{ flex: 1, overflowY: 'auto', margin: '20px 0', padding: '10px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}
      >
        {messages.map((msg, idx) => (
          <div key={idx} style={{ 
            marginBottom: '15px', 
            textAlign: msg.role === 'user' ? 'right' : 'left',
            color: msg.role === 'error' ? '#ff6b6b' : 'inherit'
          }}>
            <div style={{ 
              display: 'inline-block', 
              padding: '10px', 
              borderRadius: '10px',
              background: msg.role === 'user' ? '#007aff' : '#333',
              maxWidth: '80%'
            }}>
              {msg.text}
            </div>
          </div>
        ))}
        {isLoading && <div className="tip">CareCompass is typing...</div>}
      </div>

      {/* Input Area */}
      <div className="actions" style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask about resources or healthcare..."
          style={{ flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid #444', background: '#222', color: 'white' }}
        />
        <button 
          onClick={handleSend}
          disabled={isLoading}
          style={{ padding: '10px 20px', borderRadius: '8px', cursor: 'pointer', background: '#007aff', color: 'white', border: 'none' }}
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default App
