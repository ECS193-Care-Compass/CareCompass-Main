import { useState } from 'react'

export const Chat = () => {
   const [input, setInput] = useState('')
   const [messages, setMessages] = useState<{role: string, text: string}[]>([])

   const sendMessage = async () => {
      // Add user message to UI
      const newMessages = [...messages, { role: 'user', text: input }]
      setMessages(newMessages)
      
      // Call your Python Backend (running on localhost:8000)
      const response = await fetch('http://localhost:8000/chat', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ message: input })
      })
      
      const data = await response.json()
      setMessages([...newMessages, { role: 'bot', text: data.response }])
      setInput('')
   }

   return (
      <div>
         {/* Map through messages and render them here */}
         <input value={input} onChange={(e) => setInput(e.target.value)} />
         <button onClick={sendMessage}>Send</button>
      </div>
   )
}