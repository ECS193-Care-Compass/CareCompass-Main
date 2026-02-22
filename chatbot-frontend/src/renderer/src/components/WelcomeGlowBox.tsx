import { Button } from "./ui/button";

export const WelcomeGlowBox = () => {
  return (
    <div className="flex flex-col items-center justify-center w-full max-w-2xl px-8 py-12 transition-all duration-300 border border-transparent rounded-3xl hover:bg-white/10 hover:border-white/20 group">
      {/* Main Text */}
      <h2 className="mb-8 text-2xl font-medium text-center text-teal-900/80">
        Hello, you're safe here. I'm here to listen and provide support.
        <br />
        How can I help you today?
      </h2>


      {/* NEED TO IMPLEMENT CHAT INPUT BAR */}


      {/* The Three Option Buttons */}
      <div className="flex flex-wrap justify-center gap-4">
        <Button 
          variant="outline" 
          className="px-6 py-5 text-teal-900 border-teal-800/20 bg-white/40 rounded-2xl hover:bg-white/60 hover:border-teal-800/40"
        >
          Placeholder option 1
        </Button>
        <Button 
          variant="outline" 
          className="px-6 py-5 text-teal-900 border-teal-800/20 bg-white/40 rounded-2xl hover:bg-white/60 hover:border-teal-800/40"
        >
          Placeholder option 2
        </Button>
        <Button 
          variant="outline" 
          className="px-6 py-5 text-teal-900 border-teal-800/20 bg-white/40 rounded-2xl hover:bg-white/60 hover:border-teal-800/40"
        >
          Placeholder option 3
        </Button>
      </div>
    </div>
  );
};
