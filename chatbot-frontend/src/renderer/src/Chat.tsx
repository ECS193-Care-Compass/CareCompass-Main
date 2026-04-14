import { useState, useRef } from 'react'
import { sendChatMessage, sendVoiceChat } from './api'
import type { JSX } from 'react'

export const Chat = (): JSX.Element => {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([])
  const [isRecording, setIsRecording] = useState(false)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data)
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await handleVoiceSubmit(audioBlob)
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Error accessing microphone:', err)
      setMessages(prev => [...prev, { role: 'error', text: 'Microphone access denied' }])
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const handleVoiceSubmit = async (blob: Blob) => {
    try {
      // Show "transcribing..." status or similar if desired
      const data = await sendVoiceChat(blob)
      
      // Add both user transcript and bot response to chat history
      setMessages(prev => [
        ...prev, 
        { role: 'user', text: data.user_transcript },
        { role: 'bot', text: data.bot_response }
      ])

      // Play the response audio
      const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`)
      audio.play()
    } catch (err) {
      console.error('Voice chat failed:', err)
      setMessages(prev => [...prev, { role: 'error', text: 'Voice processing failed' }])
    }
  }

  const sendMessage = async (): Promise<void> => {
    // Add user message to UI
    const newMessages = [...messages, { role: 'user', text: input }]
    setMessages(newMessages)

    try {
      const data = await sendChatMessage(input)
      setMessages([...newMessages, { role: 'bot', text: data.response }])
    } catch (_error) {
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
            <button 
               onMouseDown={startRecording}
               onMouseUp={stopRecording}
               style={{ 
                  padding: '10px 20px', 
                  fontSize: '20px', 
                  cursor: 'pointer',
                  backgroundColor: isRecording ? '#dc3545' : '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '5px'
               }}
               title="Hold to talk"
            >
               {isRecording ? '●' : '🎤'}
            </button>
            <button onClick={sendMessage} style={{ padding: '10px 20px', fontSize: '16px', cursor: 'pointer' }}>
               Send
            </button>
         </div>
      </div>
   )
}
