import { Card } from "@/components/ui/card";
import React, { useEffect, useRef, useState, useCallback } from "react";

interface ChatWindowProps {
  children: React.ReactNode;
  shouldScrollToBottom?: boolean;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ children, shouldScrollToBottom = false }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const [lastScrollTop, setLastScrollTop] = useState(0);

  // Intelligent auto-scroll logic
  const scrollToBottom = useCallback(() => {
    if (scrollRef.current && !isUserScrolling) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isUserScrolling]);

  // Handle scroll events to detect user interaction
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10; // 10px tolerance

    // If user scrolls up, mark as user scrolling
    if (scrollTop < lastScrollTop && !isAtBottom) {
      setIsUserScrolling(true);
    }
    // If user scrolls back to bottom, resume auto-scroll
    else if (isAtBottom) {
      setIsUserScrolling(false);
    }

    setLastScrollTop(scrollTop);
  }, [lastScrollTop]);

  // Auto-scroll when content changes (if not user scrolling)
  useEffect(() => {
    if (shouldScrollToBottom) {
      // Small delay to ensure DOM has updated
      const timeoutId = setTimeout(scrollToBottom, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [shouldScrollToBottom, children, scrollToBottom]);

  // Attach scroll listener
  useEffect(() => {
    const scrollElement = scrollRef.current;
    if (scrollElement) {
      scrollElement.addEventListener('scroll', handleScroll, { passive: true });
      return () => scrollElement.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  return (
    <Card ref={scrollRef} className="flex flex-col h-full p-4 overflow-y-auto">
      {children}
    </Card>
  );
};

export default ChatWindow;
