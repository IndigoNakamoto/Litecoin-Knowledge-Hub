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
    const isProgrammaticScrollRef = useRef(false);

    // Expose scroll methods via ref
    useImperativeHandle(ref, () => ({
      scrollToElement: (element: HTMLElement | null) => {
        if (element && scrollRef.current) {
          const container = scrollRef.current;
          
          // Scroll function that recalculates position right before scrolling
          const performScroll = () => {
            // Calculate element's position relative to container using getBoundingClientRect
            const containerRect = container.getBoundingClientRect();
            const elementRect = element.getBoundingClientRect();
            
            // Get computed styles to account for padding
            const containerStyles = window.getComputedStyle(container);
            const paddingTop = parseFloat(containerStyles.paddingTop) || 0;
            
            // The element's position relative to the container's visible top edge
            const elementOffsetFromContainerTop = elementRect.top - containerRect.top;
            
            // The element's absolute position in the scrollable content
            // This is where the element actually is in the scrollable content
            const absoluteElementPosition = elementOffsetFromContainerTop + container.scrollTop;
            
            // To position the element at the top of the content area (after padding),
            // we need to scroll so that the element's absolute position minus padding equals scrollTop
            // So: scrollTop = absoluteElementPosition - paddingTop
            const targetScroll = absoluteElementPosition - paddingTop;
            
            // Check if container can actually scroll
            const maxScroll = container.scrollHeight - container.clientHeight;
            const clampedScroll = Math.min(Math.max(0, targetScroll), maxScroll);
            
            console.log('scrollToElement - performing scroll:', {
              elementTop: elementRect.top,
              containerTop: containerRect.top,
              paddingTop,
              elementOffsetFromContainerTop,
              currentScrollTop: container.scrollTop,
              absoluteElementPosition,
              targetScroll,
              clampedScroll,
              scrollHeight: container.scrollHeight,
              clientHeight: container.clientHeight,
              maxScroll
            });
            
            // Set flag to prevent scroll handler from interfering
            isProgrammaticScrollRef.current = true;
            
            // Scroll to position the element at the top of the content area (after padding)
            container.scrollTop = clampedScroll;
            
            // Verify scroll worked and retry if needed
            setTimeout(() => {
              const actualScrollTop = container.scrollTop;
              
              // Check where the element actually ended up
              const newElementRect = element.getBoundingClientRect();
              const newContainerRect = container.getBoundingClientRect();
              const finalOffset = newElementRect.top - newContainerRect.top;
              const offsetFromTarget = Math.abs(finalOffset - paddingTop);
              
              console.log('After scroll, scrollTop:', actualScrollTop, 'expected:', clampedScroll, 'elementOffsetFromTop:', finalOffset, 'paddingTop:', paddingTop, 'offsetFromTarget:', offsetFromTarget);
              
              // If element is not at the top (accounting for padding), retry with corrected calculation
              if (offsetFromTarget > 2 && container.scrollHeight > container.clientHeight) {
                console.log('Element not at top, retrying...');
                // Recalculate: current offset + current scroll = absolute position
                // We want: scrollTop = absolutePosition - paddingTop
                const retryAbsolute = finalOffset + actualScrollTop;
                const retryTarget = retryAbsolute - paddingTop;
                const retryClamped = Math.min(Math.max(0, retryTarget), maxScroll);
                console.log('Retry calculation:', { retryAbsolute, retryTarget, retryClamped });
                container.scrollTop = retryClamped;
              }
              
              isProgrammaticScrollRef.current = false;
            }, 100);
          };
          
          // Wait for layout to be ready, then scroll
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              setTimeout(performScroll, 100);
            });
          });
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
    
    // Ignore scroll events during programmatic scrolling
    if (isProgrammaticScrollRef.current) {
      return;
    }

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
