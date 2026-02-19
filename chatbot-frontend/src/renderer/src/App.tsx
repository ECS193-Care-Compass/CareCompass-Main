import { QuickExitBar } from './components/QuickExitBar';
import { ResourcesSection } from './components/ResourcesSection';
import { ChatbotWithLanguageButton } from './components/ChatbotWithLanguageButton'; 

export default function App() {
  return (
    // Changed: Added overflow-y-auto to ensure the window itself handles scrolling
    // Added font-sans and antialiased for that smooth Figma typography
    <div className="min-h-screen flex flex-col font-sans antialiased overflow-y-auto" style={{ backgroundColor: '#a1d7d6' }}>
      
      {/* 1. The Exit Bar atom */}
      <QuickExitBar />
      
      {/* 2. The Main Chat Area */}
      {/* Changed: Removed items-center/justify-center. Use padding-top to give it breathing room */}
      <section className="flex-1 w-full flex flex-col items-center pt-24 pb-12 px-4">
        <div className="w-full max-w-5xl">
          <ChatbotWithLanguageButton />
        </div>
      </section>

      {/* 3. The Footer/Resources */}
      {/* This will now sit naturally below the chat, and you can scroll to it */}
      <ResourcesSection />
      
    </div>
  );
}