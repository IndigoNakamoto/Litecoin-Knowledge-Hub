import { Card } from "@/components/ui/card";
import React from "react";

interface ChatWindowProps {
  children: React.ReactNode;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ children }) => {
  return (
    <Card className="flex flex-col h-full p-4 overflow-y-auto">
      {children}
    </Card>
  );
};

export default ChatWindow;
