// Test code for combined figma and react to put in App.tsx

import { QuickExitBar } from './components/QuickExitBar';
import { ChatbotWithLanguageButton } from './components/ChatbotWithLanguageButton';
import { ResourcesSection } from './components/ResourcesSection';

export default function App() {
  return (
    // We use min-h-screen to ensure the teal background covers the whole page
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#a1d7d6' }}>
      
      {/* 1. Safety First: The Quick Exit Bar */}
      <QuickExitBar />
      
      {/* 2. Hero Section: The Chatbot Container */}
      <section 
        className="flex-grow flex items-start justify-center px-4 pt-20 pb-8" 
        style={{ minHeight: 'calc(100vh - 48px)' }}
      >
        <div className="w-full max-w-5xl relative">
          {/* All the Chat Logic now lives inside this component */}
          <ChatbotWithLanguageButton />
        </div>
      </section>

      {/* 3. Resources Section: The "Scroll Down" Content */}
      <section className="min-h-screen bg-white px-4 py-16">
        <div className="max-w-5xl mx-auto">
           <ResourcesSection />
        </div>
      </section>
      
    </div>
  );
}