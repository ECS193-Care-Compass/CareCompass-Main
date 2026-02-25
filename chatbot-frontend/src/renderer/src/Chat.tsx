import { useState } from 'react'
import { sendChatMessage } from './api'

export const Chat = () => {
   const [input, setInput] = useState('')
   const [messages, setMessages] = useState<{role: string, text: string}[]>([])

   const sendMessage = async () => {
      // Add user message to UI
      const newMessages = [...messages, { role: 'user', text: input }]
      setMessages(newMessages)
      
      try {
        const data = await sendChatMessage(input)
        setMessages([...newMessages, { role: 'bot', text: data.response }])
      } catch (error) {
        setMessages([...newMessages, { role: 'error', text: 'Failed to connect to backend' }])
      }
      setInput('')
   }

   return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '20px' }}>
         <div style={{ flex: 1, overflowY: 'auto', marginBottom: '20px', border: '1px solid #ccc', padding: '10px', borderRadius: '5px' }}>
            {messages.map((msg, idx) => (
               <div key={idx} style={{ marginBottom: '10px', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                  <div style={{
                     display: 'inline-block',
                     maxWidth: '70%',
                     padding: '10px',
                     borderRadius: '5px',
                     backgroundColor: msg.role === 'user' ? '#007bff' : '#e9ecef',
                     color: msg.role === 'user' ? 'white' : 'black'
                  }}>
                     {msg.text}
                  </div>
               </div>
            ))}
         </div>
         <div style={{ display: 'flex', gap: '10px' }}>
            <input 
               value={input} 
               onChange={(e) => setInput(e.target.value)}
               onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
               placeholder="Type a message..."
               style={{ flex: 1, padding: '10px', fontSize: '16px' }}
            />
            <button onClick={sendMessage} style={{ padding: '10px 20px', fontSize: '16px', cursor: 'pointer' }}>
               Send
            </button>
         </div>
      </div>
   )
}
