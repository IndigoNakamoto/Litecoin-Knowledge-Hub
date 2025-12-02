'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface ScrollContextType {
  scrollPosition: number;
  setScrollPosition: (position: number) => void;
}

const ScrollContext = createContext<ScrollContextType | undefined>(undefined);

export const ScrollProvider = ({ children }: { children: ReactNode }) => {
  const [scrollPosition, setScrollPosition] = useState<number>(0);

  return (
    <ScrollContext.Provider value={{ scrollPosition, setScrollPosition }}>
      {children}
    </ScrollContext.Provider>
  );
};

export const useScrollContext = () => {
  const context = useContext(ScrollContext);
  if (context === undefined) {
    // Return default values if context is not available (for pages without ScrollProvider)
    return { scrollPosition: 0, setScrollPosition: () => {} };
  }
  return context;
};

