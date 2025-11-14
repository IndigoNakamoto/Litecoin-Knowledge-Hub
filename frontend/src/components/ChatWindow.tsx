import React, { useEffect, useRef, useState, useCallback, useImperativeHandle, forwardRef } from "react";

interface ChatWindowProps {
  children: React.ReactNode;
  shouldScrollToBottom?: boolean;
}

export interface ChatWindowRef {
  scrollToElement: (element: HTMLElement | null) => void;
  scrollToTop: () => void;
}

const ChatWindow = forwardRef<ChatWindowRef, ChatWindowProps>(
  ({ children, shouldScrollToBottom = false }, ref) => {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [isUserScrolling, setIsUserScrolling] = useState(false);
    const [lastScrollTop, setLastScrollTop] = useState(0);

    // Expose scroll methods via ref
    useImperativeHandle(ref, () => ({
      scrollToElement: (element: HTMLElement | null) => {
        if (element && scrollRef.current) {
          const container = scrollRef.current;
          
          // Get bounding rectangles
          const containerRect = container.getBoundingClientRect();
          const elementRect = element.getBoundingClientRect();
          
          // Calculate the element's position relative to the container's scrollable content
          // elementRect.top is relative to viewport, containerRect.top is container's position in viewport
          // We need to add the current scrollTop to get the absolute position in the scrollable content
          const elementPositionInScrollContent = elementRect.top - containerRect.top + container.scrollTop;
          
          // Target scroll position: element's position minus padding (16px)
          const targetScroll = elementPositionInScrollContent - 16;
          
          // Use instant scroll for immediate positioning
          container.scrollTop = Math.max(0, targetScroll);
        }
      },
      scrollToTop: () => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = 0;
        }
      },
    }));

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
      <div ref={scrollRef} className="flex flex-col h-full m-4 px-4 md:px-16 py-16 overflow-y-auto">
        {children}
      </div>
    );
  }
);

ChatWindow.displayName = "ChatWindow";

export default ChatWindow;
