import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { ArrowUp } from 'lucide-react';
import { motion } from 'framer-motion';

// Importing atoms
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { ScrollArea } from '../components/ui/scroll-area';
import { Badge } from '../components/ui/badge';
import { cn } from '../components/ui/utils'; 

interface Message {
  role: 'user' | 'ai' | 'error';
  text: string;
}

export function ChatbotWithLanguageButton() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', text: "Hello! I am CareCompass. How can I help you today?" }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [scenario, setScenario] = useState<string | null>(null);
  const [language, setLanguage] = useState<'en' | 'es'>('en');

  const handleSend = async (overrideMessage?: string) => {
    const userMessage = (overrideMessage || input).trim();
    if (!userMessage || isLoading) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMessage, scenario, lang: language }),
      });
      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'ai', text: data.response }]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'error', text: 'Connection error.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const categories = [
    { id: 'mental_health', label: 'Mental Health' },
    { id: 'practical_social', label: 'Practical Needs' },
    { id: 'legal_advocacy', label: 'Legal & Advocacy' },
  ];

  return (
    <div className="flex flex-col h-[650px] bg-white/20 backdrop-blur-md rounded-3xl border border-white/30 shadow-2xl overflow-hidden">
      
      {/* HEADER */}
      <div className="p-6 flex justify-between items-center bg-white/10 border-b border-white/20">
        <h2 className="text-xl font-bold text-cyan-900 font-sans">CareCompass AI</h2>
        <Button 
          variant="outline" 
          size="sm"
          onClick={() => setLanguage(language === 'en' ? 'es' : 'en')}
          className="rounded-full border-cyan-800 text-cyan-900 hover:bg-cyan-800 hover:text-white"
        >
          {language === 'en' ? 'ESPAÑOL' : 'ENGLISH'}
        </Button>
      </div>

      {/* CATEGORY CHIPS */}
      <div className="px-6 py-3 flex gap-2 flex-wrap bg-white/5">
        {categories.map((cat) => (
          <Badge
            key={cat.id}
            variant={scenario === cat.id ? "default" : "secondary"}
            className="cursor-pointer transition-all"
            onClick={() => setScenario(scenario === cat.id ? null : cat.id)}
          >
            {cat.label}
          </Badge>
        ))}
      </div>

      {/* MESSAGES AREA - Cleaned up nesting */}
      <ScrollArea className="flex-1 px-6">
        <div className="py-6 space-y-6">
          {messages.map((msg, idx) => (
            <motion.div 
              key={idx} 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                "flex w-full",
                msg.role === 'user' ? "justify-end" : "justify-start"
              )}
            >
              <div className={cn(
                "max-w-[80%] p-4 rounded-2xl text-sm shadow-sm",
                msg.role === 'user' 
                  ? "bg-teal-700 text-white rounded-tr-none" 
                  : "bg-white text-cyan-950 rounded-tl-none border border-white/40"
              )}>{}
                <div className="prose prose-sm prose-slate max-w-none dark:prose-invert">
                  <ReactMarkdown>{msg.text}</ReactMarkdown>
                </div>
              </div>
            </motion.div>
          ))}
          {isLoading && <div className="text-xs text-cyan-900/50 animate-pulse">Thinking...</div>}
        </div>
      </ScrollArea>

      {/* INPUT AREA */}
      <div className="p-6 bg-white/10 backdrop-blur-sm border-t border-white/20">
        <div className="relative flex items-center gap-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            className={cn(
              "h-14 rounded-2xl bg-white/90 border-0 px-5 shadow-inner transition-all",
              "focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-0",
              "placeholder:text-cyan-900/40"
            )}
            placeholder="Ask about resources or healthcare..."
          />
          <Button 
            onClick={() => handleSend()}
            size="icon"
            className={cn(
              "h-12 w-12 rounded-xl bg-teal-700 hover:bg-teal-800 shadow-lg",
              "transition-transform active:scale-95 shrink-0"
            )}
          >
            <ArrowUp className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </div> // Added missing closing tag
  );
}