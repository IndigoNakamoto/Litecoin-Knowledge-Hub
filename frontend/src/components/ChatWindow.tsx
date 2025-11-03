import { Card } from "@/components/ui/card";
import React, { useEffect, useRef } from "react";

interface ChatWindowProps {
  children: React.ReactNode;
  shouldScrollToBottom?: boolean;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ children, shouldScrollToBottom = false }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (shouldScrollToBottom && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [shouldScrollToBottom, children]);

  return (
    <Card ref={scrollRef} className="flex flex-col h-full p-4 overflow-y-auto">
      {children}
    </Card>
  );
};

export default ChatWindow;
