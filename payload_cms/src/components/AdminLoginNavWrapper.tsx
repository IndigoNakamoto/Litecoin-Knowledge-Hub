'use client';

import { useEffect, useState } from 'react';

// Lazy load the navigation to avoid Payload import map processing
let AdminLoginNav: React.ComponentType | null = null;

export default function AdminLoginNavWrapper() {
  const [mounted, setMounted] = useState(false);
  const [NavComponent, setNavComponent] = useState<React.ComponentType | null>(null);

  useEffect(() => {
    setMounted(true);
    // Dynamically import only on client side
    if (typeof window !== 'undefined') {
      import('./AdminLoginNav').then((module) => {
        AdminLoginNav = module.default;
        setNavComponent(() => AdminLoginNav);
      });
    }
  }, []);

  // Only render on client side to avoid Payload import map issues
  if (!mounted || !NavComponent) {
    return null;
  }

  return <NavComponent />;
}

