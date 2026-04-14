import { useRef, useState, useEffect } from "react"
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import ReactMarkdown from "react-markdown"
import { ArrowUp, Mic } from "lucide-react"
import { motion, AnimatePresence } from 'framer-motion'
import { sendVoiceChat, sendChatMessage } from '../api'

interface Message {
  role: "user" | "assistant" | "error"
  content: string;
  audio?: string;
}

export const WelcomeGlowBox = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isCallActive, setIsCallActive] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [callTranscript, setCallTranscript] = useState<Message[]>([]);
  const [callStartTime, setCallStartTime] = useState<number | null>(null);
  const [volume, setVolume] = useState(0);
  const [liveTranscript, setLiveTranscript] = useState("");
  
  const isCallActiveRef = useRef(false);
  const callTranscriptRef = useRef<HTMLDivElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const liveTranscriptRef = useRef<string>("");
  const chatRef = useRef<HTMLDivElement | null>(null);
  const lastMsgRef = useRef<HTMLDivElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadIntervalRef = useRef<number | null>(null);
  const playbackAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (callTranscriptRef.current) {
      callTranscriptRef.current.scrollTop = callTranscriptRef.current.scrollHeight;
    }
  }, [callTranscript]);

  useEffect(() => {
    if (lastMsgRef.current) {
      lastMsgRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Cleanup voice resources on unmount
  useEffect(() => {
    return () => {
      isCallActiveRef.current = false;
      if (playbackAudioRef.current) {
        try {
          playbackAudioRef.current.pause();
          playbackAudioRef.current.src = "";
        } catch (_e) { /* ignore */ }
        playbackAudioRef.current = null;
      }
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (_e) { /* ignore */ }
        recognitionRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        try { mediaRecorderRef.current.stop(); } catch (_e) { /* ignore */ }
      }
      if (vadIntervalRef.current) {
        window.clearInterval(vadIntervalRef.current);
        vadIntervalRef.current = null;
      }
      if (audioContextRef.current) {
        try {
          if (audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close();
          }
        } catch (_e) { /* ignore */ }
        audioContextRef.current = null;
      }
    };
  }, []);

  // --- VOICE SESSION LOGIC ---

  const startVoiceCall = async () => {
    console.log("[CALL] STEP 1: startVoiceCall button clicked.");
    // UNLOCK AUDIO: Play a tiny silent sound to let the browser allow future audio
    const unlock = new Audio("data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA");
    unlock.play().catch((e) => console.warn("[CALL] Audio unlock play failed:", e));
    
    isCallActiveRef.current = true;
    setIsCallActive(true);
    setCallTranscript([]);
    setCallStartTime(Date.now());
    console.log("[CALL] STEP 2: State set to Active. Calling startListening()...");
    await startListening();
  };

  const formatDuration = (start: number) => {
    const seconds = Math.floor((Date.now() - start) / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };
const endVoiceCall = () => {
  console.log("[CALL] endVoiceCall triggered.");
  const duration = callStartTime ? formatDuration(callStartTime) : "";
  isCallActiveRef.current = false;
  setIsCallActive(false);
  setLiveTranscript("");

  // Stop bot audio playback if it's currently speaking
  if (playbackAudioRef.current) {
    try {
      playbackAudioRef.current.pause();
      playbackAudioRef.current.currentTime = 0;
      playbackAudioRef.current.src = "";
    } catch (e) {
      console.warn("Error stopping playback audio:", e);
    }
    playbackAudioRef.current = null;
  }
  setIsSpeaking(false);

  if (recognitionRef.current) {
    try { recognitionRef.current.stop(); } catch (e) {}
    recognitionRef.current = null;
  }

  if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
    mediaRecorderRef.current.stop();
  }

  setIsRecording(false);
  setIsLoading(false);
  cleanupAudio();

  setMessages(prev => [
    ...prev,
    { role: "assistant", content: `**Voice chat ended**\n\n${duration}` }
  ]);
};

  const cleanupAudio = () => {
    liveTranscriptRef.current = "";
    setLiveTranscript("");
    if (vadIntervalRef.current) {
      window.clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        if (audioContextRef.current.state !== 'closed') {
          audioContextRef.current.close();
        }
      } catch (e) {
        console.warn("Error closing audio context:", e);
      }
      audioContextRef.current = null;
    }
    analyserRef.current = null;
  };

  const startListening = async () => {
    console.log("[VAD] STEP 3: startListening entry point.");
    if (!isCallActiveRef.current) {
      console.log("[VAD] ABORTED: isCallActiveRef is false");
      return;
    }
    
    try {
      liveTranscriptRef.current = "";
      setLiveTranscript("");
      // --- Web Speech API (Live Transcription) ---
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event: any) => {
          const finalResult = Array.from(event.results)
            .map((res: any) => res[0].transcript)
            .join('');

          liveTranscriptRef.current = finalResult;
          setLiveTranscript(finalResult);
          console.log(`[LIVE] ${finalResult}`);
        };

        recognition.onerror = (event: any) => console.error('[SPEECH] Recognition error', event.error);
        recognition.onend = () => console.log('[SPEECH] Recognition ended');
        
        recognition.start();
        recognitionRef.current = recognition;
      }
      // ---------------------------------------------
      console.log("[VAD] STEP 4: Requesting microphone access...");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log("[VAD] STEP 5: Microphone access GRANTED.");
      
      // Setup VAD (Voice Activity Detection)
      console.log("[VAD] STEP 6: Initializing AudioContext (16kHz)...");
      const audioContext = new AudioContext({ sampleRate: 16000 });
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
        console.log("[VAD] AudioContext resumed from suspended state.");
      }
      
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      console.log("[VAD] STEP 7: Audio pipeline ready.");

      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      
      mediaRecorder.onstop = async () => {
        // 1. Capture chunks and clear ref immediately
        const chunks = [...audioChunksRef.current];
        audioChunksRef.current = [];

        const audioBlob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });
        // Use ref (not state) to get the latest transcript — avoids stale closure
        const finalTranscript = liveTranscriptRef.current;
        console.log(`[VAD] MediaRecorder stopped. Size: ${audioBlob.size} bytes, Transcript: "${finalTranscript}"`);

        // 2. Release hardware IMMEDIATELY before starting the upload
        if (recognitionRef.current) {
          try { recognitionRef.current.stop(); } catch (e) {}
          recognitionRef.current = null;
        }
        stream.getTracks().forEach(track => track.stop());

        // 3. Process the turn — always send if audio blob has meaningful data
        // Audio blob > 5000 bytes likely contains actual speech
        if (finalTranscript.trim().length > 0 || audioBlob.size > 5000) {
          await handleCallTurn(audioBlob, finalTranscript);
        } else {
          console.log("[VAD] No speech detected. Resuming listening.");
          if (isCallActiveRef.current) startListening();
        }
      };

      console.log("[VAD] STEP 8: Starting MediaRecorder...");
      mediaRecorder.start(250); 
      setIsRecording(true);
      console.log("[VAD] SUCCESS: Listening turn started.");

      // VAD Loop: Detect silence
      let silenceDuration = 0;
      const turnStartTime = Date.now();
      const checkInterval = 100; // Slightly slower check for stability
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      vadIntervalRef.current = window.setInterval(() => {
        analyser.getByteFrequencyData(dataArray);
        
        // Sum the amplitude across frequencies
        const sum = dataArray.reduce((a, b) => a + b, 0);
        const average = sum / dataArray.length;
        setVolume(average * 2); // Visual feedback boost

        // SILENCE DETECTION LOGIC (Using a more reliable average)
        if (average < 10) { // Very sensitive to catch quiet voices
          silenceDuration += checkInterval;
        } else {
          silenceDuration = 0; 
        }

        // After 1.5 seconds of silence, stop recording and send to backend
        if (silenceDuration > 1500) {
          if (mediaRecorder.state === "recording") {
            window.clearInterval(vadIntervalRef.current!);
            vadIntervalRef.current = null;
            console.log("[VAD] 1.5s Silence detected. Stopping recorder.");
            mediaRecorder.stop();
            setIsRecording(false);
          }
        }

        // Safety timeout: 15 seconds max per turn
        if (Date.now() - turnStartTime > 15000) {
          if (mediaRecorder.state === "recording") {
            window.clearInterval(vadIntervalRef.current!);
            mediaRecorder.stop();
            setIsRecording(false);
            console.log("VAD: Timeout reached, stopping.");
          }
        }
      }, checkInterval);

    } catch (err) {
      console.error('Microphone error:', err);
      setIsCallActive(false);
    }
  };

  const handleCallTurn = async (blob: Blob, transcript?: string) => {
    if (!isCallActiveRef.current) {
      console.log("[DEBUG] handleCallTurn aborted: isCallActiveRef is false");
      return;
    }
    console.log(`[DEBUG] handleCallTurn started. Blob size: ${blob.size} bytes, Transcript provided: ${!!transcript}`);
    setIsLoading(true);
    cleanupAudio(); 
    
    try {
      console.log(`[DEBUG] Calling sendVoiceChat API...`);
      const data = await sendVoiceChat(blob, undefined, transcript);
      console.log(`[DEBUG] API response received:`, data);
      
      // If the backend didn't find any speech, just start listening again
      if (!data.user_transcript || !data.bot_response) {
        console.log("[DEBUG] No transcript or response from backend, skipping turn.");
        if (isCallActiveRef.current) startListening();
        return;
      }

      const userMsg: Message = { role: "user", content: data.user_transcript };
      const aiMsg: Message = {
        role: "assistant",
        content: data.bot_response, 
        audio: data.audio_base64 
      };

      const newItems = [userMsg, aiMsg];
      setMessages(prev => [...prev, ...newItems]);
      setCallTranscript(prev => [...prev, ...newItems]);

      if (data.audio_base64) {
        // Abort if the user ended the call while waiting for the response
        if (!isCallActiveRef.current) {
          console.log("[DEBUG] Audio: Call ended before playback, aborting.");
          return;
        }
        setIsSpeaking(true);
        console.log(`[DEBUG] Audio: Received base64 data, length: ${data.audio_base64.length}`);
        const audio = new Audio(`data:audio/mpeg;base64,${data.audio_base64}`);
        audio.volume = 1.0;
        playbackAudioRef.current = audio;

        audio.oncanplaythrough = () => {
          console.log(`[DEBUG] Audio: Ready to play. Duration: ${audio.duration.toFixed(2)}s`);
        };

        audio.onplay = () => console.log("[DEBUG] Audio: Playback started successfully.");

        audio.onended = () => {
          console.log("[DEBUG] Audio: Playback finished.");
          playbackAudioRef.current = null;
          setIsSpeaking(false);
          if (isCallActiveRef.current) startListening();
        };

        audio.onerror = () => {
          const error = audio.error;
          console.error("[DEBUG] Audio: ERROR during playback:", {
            code: error?.code,
            message: error?.message
          });
          playbackAudioRef.current = null;
          setIsSpeaking(false);
          if (isCallActiveRef.current) startListening();
        };

        try {
          console.log("[DEBUG] Audio: Attempting to play...");
          await audio.play();
        } catch (err) { 
          console.error("[DEBUG] Audio: Playback REJECTED by browser:", err);
          setIsSpeaking(false);
          if (isCallActiveRef.current) startListening(); 
        }
      } else {
        console.warn("[DEBUG] Audio: No audio data received from backend.");
        if (isCallActiveRef.current) startListening();
      }
    } catch (err) {
      console.error("[DEBUG] CRITICAL error in handleCallTurn:", err);
      if (isCallActiveRef.current) startListening();
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (override?: string) => {
    const text = (override ?? input).trim();
    if (!text || isLoading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsLoading(true);
    
    try {
      const data = await sendChatMessage(text);
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "error", content: "Connection error." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const GUIDED_PROMPTS = [
    { label: "Mental Health Support", scenario: "mental_health" },
    { label: "Practical Needs Help", scenario: "practical_social" },
    { label: "Legal & Advocacy Help", scenario: "legal_advocacy" },
  ];

  return (
    <div className="relative flex flex-col w-full max-w-[min(90vw,70rem)] mx-auto mt-0 px-4 sm:px-6 md:px-12 py-2 h-[80vh] sm:h-[75vh] md:h-[70vh] max-h-[calc(100vh-12rem)] transition-all duration-300 border border-transparent rounded-3xl hover:bg-transparent hover:border-teal-700/40">
      
      {/* --- CALL MODE OVERLAY --- */}
      <AnimatePresence>
        {isCallActive && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 bg-[#002b2b] flex flex-col items-center justify-between py-12 rounded-3xl"
          >
            <div className="text-teal-100/40 text-xs uppercase tracking-[0.2em] font-bold">Voice Session Active</div>
            
            <div className="flex-1 w-full flex flex-col items-center justify-center gap-12 px-6 overflow-hidden">
              {/* Mic Icon with Contained Pulse */}
              <div className="relative w-32 h-32 flex items-center justify-center">
                <motion.div 
                  animate={{ 
                    scale: isRecording ? 1 + (volume / 200) : 1,
                    boxShadow: isRecording ? `0 0 ${15 + (volume / 4)}px rgba(20, 184, 166, 0.3)` : "none",
                  }}
                  transition={{ type: "spring", stiffness: 300, damping: 25 }}
                  className="w-20 h-20 bg-teal-500/20 border border-teal-400/30 rounded-full flex items-center justify-center relative z-10 overflow-hidden"
                >
                  {isRecording && (
                    <motion.div 
                      initial={{ scale: 0.5, opacity: 0 }}
                      animate={{ scale: 1.2, opacity: [0, 0.5, 0] }}
                      transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                      className="absolute inset-0 bg-teal-400/20 rounded-full"
                    />
                  )}
                  <Mic size={28} className={`${isRecording ? "text-teal-300" : "text-white/20"} transition-colors`} />
                </motion.div>
              </div>

              {/* Immersive Transcript (No Frame) */}
              <div className="w-full max-w-2xl flex-1 flex flex-col items-center justify-center gap-6">
                <p className="text-teal-200 text-lg font-medium text-center animate-pulse">
                  {isRecording ? "Listening..." : isSpeaking ? "Speaking..." : isLoading ? "Thinking..." : "Starting..."}
                </p>
                
                <div 
                  ref={callTranscriptRef}
                  className="w-full flex-1 overflow-y-auto no-scrollbar mask-fade-edges flex flex-col gap-4 py-4"
                >
                  <AnimatePresence mode="popLayout">
                    {callTranscript.map((msg, idx) => (
                      <motion.div 
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`w-full flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                      >
                        <p className={`max-w-[85%] text-sm leading-relaxed ${msg.role === "user" ? "text-teal-300 text-right font-medium" : "text-white/80 text-left"}`}>
                          {msg.content}
                        </p>
                      </motion.div>
                    ))}

                    {/* Live Transcript (Floating) */}
                    {isRecording && liveTranscript && (
                      <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="w-full flex justify-center"
                      >
                        <div className="flex flex-col items-center gap-2">
                          <p className="text-white text-base text-center italic font-light tracking-wide px-4">
                            {liveTranscript}
                          </p>
                          <div className="flex gap-1.5 h-1 items-center">
                            <span className="w-1 h-1 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-1 h-1 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-1 h-1 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>

            <button 
              onClick={endVoiceCall}
              className="group mb-4 px-8 py-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-full font-bold hover:bg-red-500 hover:text-white transition-all flex items-center gap-3 active:scale-95"
            >
              <div className="w-2 h-2 bg-current rounded-full animate-pulse" />
              End Voice Chat
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div ref={chatRef} className="flex-1 w-full overflow-y-auto px-4 py-4 flex flex-col">
        <div className={`space-y-4 ${messages.length === 0 ? 'flex-1 flex items-center justify-center' : ''}`}>
            {messages.length === 0 ? (
              <h2 className="text-2xl font-medium text-center text-teal-900/80">
                Hello, you're safe here. I'm here to listen and provide support.
                <br />
                How can I help you today?
              </h2>
            ) : (
              <>
                {messages.map((m, i) => (
                  <motion.div
                    ref={i === messages.length - 1 ? lastMsgRef : null}
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div className={`max-w-[80%] p-3 rounded-lg text-sm ${m.role === "user" ? "bg-teal-700 text-white rounded-tr-none" : "bg-white/40 text-cyan-950 shadow-sm rounded-tl-none"}`}>
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    </div>
                  </motion.div>
                ))}
                {isLoading && <div className="text-xs text-cyan-800 animate-pulse">Thinking...</div>}
              </>
            )}
          </div>
        </div>

      <div className="flex flex-wrap justify-center gap-4 mt-2">
        <AnimatePresence mode="wait">
          {isLoading && (
            <motion.div
              key="loading-dots"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="flex items-center gap-1 text-teal-900"
            >
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="text-4xl"
                  animate={{ y: [0, -10, 0] }}
                  transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15, ease: "easeInOut" }}
                >
                  •
                </motion.span>
              ))}
            </motion.div>
          )}
          {!isLoading && (
            <motion.div
              key="options"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="flex flex-wrap justify-center gap-4"
            >
              {GUIDED_PROMPTS.map((p) => (
                <Button
                  key={p.label}
                  variant="outline"
                  onClick={() => sendMessage(p.label)}
                  className="px-6 py-3 text-teal-900 border-teal-800/20 bg-white/40 rounded-2xl hover:bg-white/60 hover:border-teal-800/40"
                >
                  {p.label}
                </Button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="w-full mt-4 p-4 bg-transparent">
        <div className="relative flex items-center gap-2">
          <div className="relative flex-grow">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') sendMessage(); }}
              placeholder={isCallActive ? "Voice Agent is active..." : "How can I help you safely?"}
              className={`w-full bg-white/40 border-none rounded-xl py-4 md:py-5 pl-4 pr-12 text-sm focus:ring-2 focus:ring-teal-700/40 ${isCallActive ? 'ring-2 ring-teal-500/50' : ''}`}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-teal-600 text-white rounded-full hover:bg-teal-700 disabled:bg-teal-600/50 disabled:text-white/70"
            >
              <ArrowUp size={18} />
            </button>
          </div>
          
          <button
            onClick={startVoiceCall}
            className="p-2.5 bg-teal-600 text-white rounded-full hover:bg-teal-700 transition-all duration-200"
            aria-label="Use Voice"
            title="Use Voice"
          >
            <Mic size={20} />
          </button>
        </div>
        {isCallActive && isSpeaking && (
          <p className="text-center text-xs text-teal-600 mt-2 font-medium italic animate-pulse">Agent is speaking...</p>
        )}
        {isCallActive && isRecording && !isSpeaking && !isLoading && (
          <p className="text-center text-xs text-teal-600 mt-2 font-medium">Agent is listening...</p>
        )}
        {isLoading && isCallActive && (
          <p className="text-center text-xs text-teal-600 mt-2 font-medium">Thinking...</p>
        )}
      </div>
    </div>
  );
};
