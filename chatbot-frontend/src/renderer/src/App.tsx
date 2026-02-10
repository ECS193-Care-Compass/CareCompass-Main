import { useState, useEffect, useRef } from 'react'

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

  const handleSend = async (): Promise<void> => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }])
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8080/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          sessionId: 'test-session', 
          message: userMessage 
        }),
      })

      const data = await response.json()
      setMessages((prev) => [...prev, { role: 'ai', text: data.reply || data.message }])
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'error', text: 'Failed to connect to backend.' }])
    } finally {
      setIsLoading(false)
    }
  }

  // Quick reply options
  const quickReplies = [
    "What local resources are available?",
    "I need help finding healthcare.",
    "Can you explain my options?"
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
        background: '#005f63'   // DARK TEAL BACKGROUND
      }}
    >

    {/* 🔵 QUICK EXIT TOP BAR */}
    <div 
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        padding: '10px 20px',
        background: '#005f63',   // DARK TEAL
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
          background: '#4fd1c5',   // LIGHT TEAL
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

      {/* Header shifted down because of top bar */}
      <header style={{ marginTop: '50px' }}>
        <h2 className="text">CareCompass AI</h2>
      </header>

      {/* Message Display Area */}
      <div 
        ref={scrollRef}
        style={{ 
          flex: 1, 
          overflowY: 'auto', 
          margin: '20px 0', 
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
              maxWidth: '80%'
            }}>
              {msg.text}
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
            onClick={() => setInput(text)}
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
          onClick={handleSend}
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
