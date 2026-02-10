import { useMemo, useState } from 'react'
import { sendChatMessage } from './api'

export const Chat = () => {
   const [input, setInput] = useState('')
   const [messages, setMessages] = useState<{role: string, text: string}[]>([])
   const sessionId = useMemo(() => {
      if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
         return `session-${crypto.randomUUID()}`
      }
      return `session-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
   }, [])

   const sendMessage = async () => {
      // Add user message to UI
      const newMessages = [...messages, { role: 'user', text: input }]
      setMessages(newMessages)
      
      const data = await sendChatMessage(input, sessionId, { anonymous: true })
      setMessages([...newMessages, { role: 'bot', text: data.reply }])
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
