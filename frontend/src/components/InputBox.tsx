import { Button } from "@/components/ui/button";
import React, { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";

interface InputBoxProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

const MAX_QUERY_LENGTH = 1000;

const InputBox: React.FC<InputBoxProps> = ({ onSendMessage, isLoading }) => {
  const [input, setInput] = useState("");
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
    <div className="sticky bottom-0 inset-x-0 z-10 ">
      <div className="mx-auto max-w-4xl px-4 py-4">
        <div className="relative flex items-end gap-3 rounded-2xl border border-border bg-card text-foreground shadow-lg shadow-black/20 transition-all focus-within:border-primary/60 focus-within:shadow-xl focus-within:shadow-primary/10">
          <textarea
            ref={textareaRef}
            placeholder="Ask anything about Litecoin..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            disabled={isLoading}
            rows={1}
            className="flex-1 resize-none border-0 bg-transparent px-4 py-3.5 text-[16px] leading-7 text-[#222222] placeholder:text-gray-500 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 min-h-[56px] max-h-[200px] overflow-y-auto"
            style={{
              scrollbarWidth: "thin",
              scrollbarColor: "var(--muted) transparent",
            }}
          />
          <div className="flex items-end pb-2 pr-2">
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              size="icon"
              className="h-9 w-9 rounded-xl bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed transition-all shrink-0"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="mt-2 flex justify-between items-center px-4">
          <p className="text-sm text-muted-foreground">
            Press Enter to send, Shift+Enter for new line
          </p>
          <p className={`text-sm ${
            input.length > MAX_QUERY_LENGTH 
              ? 'text-red-500 font-semibold' 
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
