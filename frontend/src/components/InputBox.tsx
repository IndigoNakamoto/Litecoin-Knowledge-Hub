import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import React, { useState } from "react";

interface InputBoxProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

const InputBox: React.FC<InputBoxProps> = ({ onSendMessage, isLoading }) => {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input);
      setInput("");
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !isLoading) {
      handleSend();
    }
  };

  return (
    <div className="flex gap-2 p-4">
      <Input
        placeholder="Ask a question about Litecoin..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        disabled={isLoading}
      />
      <Button onClick={handleSend} disabled={!input.trim() || isLoading}>
        Send
      </Button>
    </div>
  );
};

export default InputBox;
