import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'

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
  const [scenario, setScenario] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight)
  }, [messages])

  // ESC key quick exit
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        window.location.href = "https://weather.com"
      }
    }
    window.addEventListener("keydown", handleEsc)
    return () => window.removeEventListener("keydown", handleEsc)
  }, [])

  const handleSend = async (overrideMessage?: string): Promise<void> => {
    const userMessage = (overrideMessage || input).trim()
    if (!userMessage || isLoading) return

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }])
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: userMessage,
          scenario: scenario
        }),
      })

      const data = await response.json()
      setMessages((prev) => [...prev, { role: 'ai', text: data.response }])
    } catch (error) {
      setMessages((prev) => [...prev, { 
        role: 'error', 
        text: 'Failed to connect to backend. Make sure the API is running (uvicorn api:app --port 8000).' 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearChat = async (): Promise<void> => {
    try {
      await fetch('http://localhost:8000/clear', { method: 'POST' })
    } catch (e) {
      // Ignore if backend is down
    }
    setMessages([{ role: 'ai', text: 'Hello! I am CareCompass. How can I help you today?' }])
    setScenario(null)
  }

  // Quick reply options
  const quickReplies = [
    "What local resources are available?",
    "I need help finding healthcare.",
    "Can you explain my options?"
  ]

  // Scenario categories
  const categories = [
    { id: 'immediate_followup', label: 'Medical Follow-Up' },
    { id: 'mental_health', label: 'Mental Health' },
    { id: 'practical_social', label: 'Practical Needs' },
    { id: 'legal_advocacy', label: 'Legal & Advocacy' },
    { id: 'delayed_ambivalent', label: 'Delayed Follow-Up' },
  ]

  return (
    <div 
      className="container" 
      style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        height: '100vh', 
        padding: '20px',
        position: 'relative',
        background: '#66c2c2'  
      }}
    >

    {/* QUICK EXIT TOP BAR */}
    <div 
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        padding: '10px 20px',
        background: '#005f63',
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '14px',
        fontWeight: 500,
        zIndex: 9999,
        pointerEvents: 'auto',
        borderRadius: '0 0 8px 8px'
      }}
    >
      <span>Press ESC or click the button to quickly leave this site</span>

      <button
        onClick={() => window.location.replace("https://weather.com")}
        style={{
          background: '#4fd1c5',
          color: '#003f42',
          border: 'none',
          padding: '6px 12px',
          borderRadius: '6px',
          cursor: 'pointer',
          fontWeight: 600
        }}
      >
        Quick Exit
      </button>
    </div>

      {/* Header */}
      <header style={{ marginTop: '50px' }}>
        <h2 className="text">CareCompass AI</h2>
      </header>

      {/* Scenario Category Selector */}
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '10px' }}>
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setScenario(scenario === cat.id ? null : cat.id)}
            style={{
              padding: '6px 12px',
              borderRadius: '16px',
              background: scenario === cat.id ? '#4fd1c5' : '#333',
              color: scenario === cat.id ? '#003f42' : 'white',
              border: scenario === cat.id ? '2px solid #4fd1c5' : '1px solid #555',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: scenario === cat.id ? 600 : 400
            }}
          >
            {cat.label}
          </button>
        ))}
        {scenario && (
          <button
            onClick={handleClearChat}
            style={{
              padding: '6px 12px',
              borderRadius: '16px',
              background: 'transparent',
              color: '#ff6b6b',
              border: '1px solid #ff6b6b',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Clear Chat
          </button>
        )}
      </div>

      {/* Message Display Area */}
      <div 
        ref={scrollRef}
        style={{ 
          flex: 1, 
          overflowY: 'auto', 
          margin: '10px 0', 
          padding: '10px', 
          background: 'rgba(255,255,255,0.05)', 
          borderRadius: '8px' 
        }}
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
              maxWidth: '80%',
              textAlign: 'left'
            }}>
              {msg.role === 'user' ? (
                msg.text
              ) : (
                <ReactMarkdown
                  components={{
                    p: ({ children }) => <p style={{ margin: '0 0 8px 0' }}>{children}</p>,
                    strong: ({ children }) => <strong style={{ color: '#4fd1c5' }}>{children}</strong>,
                    ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: '20px' }}>{children}</ul>,
                    ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: '20px' }}>{children}</ol>,
                    li: ({ children }) => <li style={{ marginBottom: '4px' }}>{children}</li>,
                  }}
                >
                  {msg.text}
                </ReactMarkdown>
              )}
            </div>
          </div>
        ))}
        {isLoading && <div className="tip">CareCompass is typing...</div>}
      </div>

      {/* Quick Reply Buttons */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
        {quickReplies.map((text, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(text)}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '8px',
              background: '#444',
              color: 'white',
              border: '1px solid #666',
              cursor: 'pointer'
            }}
          >
            {text}
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="actions" style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask about resources or healthcare..."
          style={{ 
            flex: 1, 
            padding: '12px', 
            borderRadius: '8px', 
            border: '1px solid #444', 
            background: '#222', 
            color: 'white' 
          }}
        />
        <button 
          onClick={() => handleSend()}
          disabled={isLoading}
          style={{ 
            padding: '10px 20px', 
            borderRadius: '8px', 
            cursor: 'pointer', 
            background: '#007aff', 
            color: 'white', 
            border: 'none' 
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default App