# CARE Bot Voice AI Agent Implementation

This document details the architecture and implementation steps taken to integrate the Voice AI Agent into the CARE Bot system.

## 1. Architectural Overview
The Voice AI Agent operates on a **Hybrid-Real-Time** model, combining local browser capabilities with cloud-based AI services for maximum speed and accuracy.

### The Flow:
1.  **Input**: The user speaks into the microphone.
2.  **Live Transcription**: The browser's **Web Speech API** captures and displays the words instantly on-screen.
3.  **Voice Activity Detection (VAD)**: A local algorithm monitors volume and timing. After a **1.5-second pause**, it automatically stops the recorder.
4.  **Backend Processing**:
    *   The frontend sends the transcribed text (and raw audio as fallback) to the FastAPI `/voice-chat` endpoint.
    *   The backend performs a **Trauma-Informed RAG** search using ChromaDB.
    *   **Google Gemini** generates a compassionate, principle-aligned response.
5.  **Voice Synthesis**: **AWS Polly (Neural)** converts the response into high-quality human-like speech.
6.  **Output**: The frontend receives the response text and base64 audio, plays the sound, and displays the response.

---

## 2. Key Features Implemented

### Performance & Accuracy
*   **Live Transcription**: Words appear as you speak, eliminating the "black box" feeling of waiting for a transcription job.
*   **Zero-Latency Hybrid Mode**: By sending text directly from the browser to the LLM, we bypass the 5-8 second delay usually required by cloud transcription jobs.
*   **0.2s Polling**: If raw audio must be used, the backend polls AWS Transcribe every 200ms for near-instant results.

### Robustness
*   **State Protection**: Uses `useRef` hooks to manage call state, preventing React race conditions and ensuring the agent never stops listening mid-sentence.
*   **Smart Silence Detection**: Set to a sensitive threshold (10) to catch quiet voices, with a 3-second patience window for long thoughts.
*   **Automatic Cleanup**: Releases microphone hardware and closes AudioContexts immediately after use to prevent memory leaks or system hangs.

### Immersive UI
*   **Frame-less Design**: A modern, immersive overlay where text floats naturally, removing cluttered boxes and borders.
*   **Reactive Mic**: The microphone icon glows and pulses in real-time based on the actual volume of the user's voice.
*   **Session Summary**: Automatically calculates and displays the total session duration (e.g., `Voice chat ended — 3m 25s`).

---

## 3. Detailed Code Changes

### Backend (Python/FastAPI)
*   **`api.py`**:
    *   Modified `@app.post("/voice-chat")` to accept optional `text` fields.
    *   Implemented a "Fallback Guard": if no speech is detected, the bot speaks a prompt: *"I'm sorry, I didn't quite catch that..."*
    *   Added deep instrumentation for timing each step (S3 upload, RAG, Polly).
*   **`src/utils/voice_service.py`**:
    *   Optimized AWS Transcribe polling from 1.0s to 0.2s.
    *   Added fallback logic for S3 bucket detection.
    *   Forced 16,000Hz sample rate for better recognition.

### Frontend (React/Electron)
*   **`chatbot-frontend/src/renderer/src/api.ts`**:
    *   Updated `sendVoiceChat` to support multipart `File` objects (improving Chromium network pipe stability).
    *   Added support for sending pre-transcribed text to the backend.
*   **`WelcomeGlowBox.tsx`**:
    *   **Web Speech Integration**: Added `window.webkitSpeechRecognition` logic.
    *   **VAD Logic**: Re-wrote the recording loop using `requestAnimationFrame` for smoother volume tracking.
    *   **UI Overhaul**: Replaced the boxed layout with a borderless, immersive vertical flex layout.
    *   **Race Condition Fix**: Implemented `isCallActiveRef` to ensure asynchronous callbacks always have the correct state.

---

## 4. How to Run
1.  **Configure AWS**: Ensure `GOOGLE_API_KEY`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` are in your `.env`.
2.  **Start Backend**: `python api.py` (Runs on port 8000).
3.  **Start Frontend**: `npm run dev` in the `chatbot-frontend` folder.
4.  **Use**: Click the **Mic** icon in the chat bar to enter immersive voice mode.
