'use client';

import React, { createContext, useContext, useState, ReactNode, useCallback } from 'react';

interface ScrollContextType {
  scrollPosition: number;
  setScrollPosition: (position: number) => void;
  pinnedMessageId: string | null;
  setPinnedMessageId: (id: string | null) => void;
  resetPinningContext: () => void;
}

const ScrollContext = createContext<ScrollContextType | undefined>(undefined);

export const ScrollProvider = ({ children }: { children: ReactNode }) => {
  const [scrollPosition, setScrollPosition] = useState<number>(0);
  const [pinnedMessageId, setPinnedMessageId] = useState<string | null>(null);

  const resetPinningContext = useCallback(() => {
    setPinnedMessageId(null);
  }, []);

  return (
    <ScrollContext.Provider value={{ 
      scrollPosition, 
      setScrollPosition,
      pinnedMessageId,
      setPinnedMessageId,
      resetPinningContext
    }}>
      {children}
    </ScrollContext.Provider>
  );
};

export const useScrollContext = () => {
  const context = useContext(ScrollContext);
  if (context === undefined) {
    // Return default values if context is not available (for pages without ScrollProvider)
    return { 
      scrollPosition: 0, 
      setScrollPosition: () => {},
      pinnedMessageId: null,
      setPinnedMessageId: () => {},
      resetPinningContext: () => {}
    };
  }
  return context;
};

