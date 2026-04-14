import { useState, useRef, useEffect } from 'react'
import type { JSX } from 'react'
import { ArrowUp, Mic } from 'lucide-react'
import { sendChatMessage, sendVoiceChat } from '../api'

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
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

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
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
      if (!hasStarted) setHasStarted(true)
    } catch (err) {
      console.error('Error accessing microphone:', err)
      const errorMessage: Message = {
        id: Date.now().toString(),
        text: "I couldn't access your microphone. Please check your browser permissions.",
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const handleVoiceSubmit = async (blob: Blob) => {
    setIsProcessing(true)
    try {
      const data = await sendVoiceChat(blob)
      
      const userMessage: Message = {
        id: Date.now().toString(),
        text: data.user_transcript,
        isUser: true,
        timestamp: new Date()
      }

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.bot_response,
        isUser: false,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, userMessage, botMessage])

      // Play the response audio
      if (data.audio_base64) {
        const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`)
        audio.play().catch(e => console.error("Audio playback failed:", e))
      }
    } catch (err) {
      console.error('Voice chat failed:', err)
      const errorMessage: Message = {
        id: Date.now().toString(),
        text: "Sorry, I had trouble processing your voice message. Please try again or type your message.",
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsProcessing(false)
    }
  }

  const handleSendMessage = async (messageText?: string, scenario?: string) => {
    const textToSend = messageText || inputValue.trim();
    if (!textToSend || isProcessing) return;

    if (!hasStarted) setHasStarted(true);

    const userMessage: Message = {
      id: Date.now().toString(),
      text: textToSend,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsProcessing(true);

    try {
      const data = await sendChatMessage(textToSend, scenario);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.response,
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "I'm having trouble connecting to my brain right now. Please make sure the backend server is running.",
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
    }
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
              onClick={() => handleSendMessage(prompt.label, prompt.scenario)}
              className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-full text-sm transition-colors disabled:opacity-50"
              disabled={isProcessing}
            >
              {prompt.label}
            </button>
          ))}
          
        </div>
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-slate-200">
        <div className="flex items-center gap-2">
          <div className="relative flex-grow">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isRecording ? "Listening..." : "Type your message..."}
              className={`w-full pl-4 pr-12 py-3 bg-slate-50 border rounded-2xl focus:outline-none focus:ring-2 focus:ring-slate-300 text-sm transition-all ${
                isRecording ? 'border-red-400 ring-2 ring-red-100' : 'border-slate-200'
              }`}
              disabled={isProcessing}
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || isProcessing}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-slate-800 text-white rounded-full hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
              aria-label="Send message"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>
          <button
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            disabled={isProcessing}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
              isRecording 
                ? 'bg-red-500 text-white animate-pulse scale-110 shadow-lg' 
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title="Hold to talk"
          >
            <Mic className={`w-5 h-5 ${isRecording ? 'fill-current' : ''}`} />
          </button>
        </div>
        {isRecording && (
          <p className="text-center text-xs text-red-500 mt-2 font-medium">Recording... Release to send</p>
        )}
        {isProcessing && !isRecording && (
          <p className="text-center text-xs text-slate-400 mt-2">Thinking...</p>
        )}
      </div>
    </div>
  );
}
