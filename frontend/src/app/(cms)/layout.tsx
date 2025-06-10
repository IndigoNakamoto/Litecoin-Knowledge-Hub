'use client';

import { AuthProvider } from '@/contexts/AuthContext';
import '../globals.css'; // Import global styles if needed

export default function CmsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </AuthProvider>
  );
}
