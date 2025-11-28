import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles } from "lucide-react";

interface InputBoxProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

const MAX_QUERY_LENGTH = 400;

const InputBox: React.FC<InputBoxProps> = ({ onSendMessage, isLoading }) => {
  const [input, setInput] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput("");
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !isLoading) {
      event.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <div 
      className="sticky bottom-0 inset-x-0 z-10 mt-4"
    >
      <div className="mx-auto max-w-4xl px-4 py-4">
        <div 
          className="relative flex items-end gap-3 rounded-2xl border border-border text-foreground shadow-lg shadow-black/20 transition-all focus-within:border-primary/60 focus-within:shadow-xl focus-within:shadow-primary/10"
          style={{
            backdropFilter: 'blur(30px)',
            WebkitBackdropFilter: 'blur(30px)',
          }}
        >
          {/* Litecoin logo/sparkles on focus */}
          {isFocused && (
            <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
              <Sparkles className="h-4 w-4 text-primary animate-sparkle" />
            </div>
          )}
          <textarea
            ref={textareaRef}
            placeholder="Ask anything about Litecoin..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            disabled={isLoading}
            rows={1}
            className={`flex-1 resize-none border-0 bg-transparent py-3.5 text-[16px] leading-7 text-foreground placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 min-h-[56px] max-h-[200px] overflow-y-auto transition-all ${
              isFocused ? 'pl-12 pr-4' : 'px-4'
            }`}
            style={{
              scrollbarWidth: "thin",
              scrollbarColor: "var(--muted) transparent",
            }}
          />
          <div className="flex items-end pb-2 pr-2">
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="h-10 w-10 rounded-xl bg-gradient-to-r from-primary to-primary/80 border border-primary/20 text-white shadow-lg hover:shadow-xl hover:shadow-primary/10 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shrink-0 hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 flex items-center justify-center"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="mt-2 flex justify-between items-center px-4">
          <p className="text-sm text-muted-foreground">
            Press Enter to send, Shift+Enter for new line
          </p>
          <p className={`text-sm font-medium ${
            input.length > MAX_QUERY_LENGTH 
              ? 'text-red-500' 
              : input.length > MAX_QUERY_LENGTH * 0.9 
                ? 'text-yellow-500' 
                : 'text-muted-foreground'
          }`}>
            {input.length}/{MAX_QUERY_LENGTH}
          </p>
        </div>
      </div>
    </div>
  );
};

export default InputBox;
