import Navigation from '@/components/NavigationMain';
import { AuthProvider } from '@/contexts/AuthContext';
import { ScrollProvider } from '@/contexts/ScrollContext';
import type { Metadata } from 'next';
import { Geist, Geist_Mono, Space_Grotesk, Inter } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  variable: '--font-space-grotesk',
  subsets: ['latin'],
  display: 'swap',
});

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: "Litecoin - Chat",
  description: "Litecoin Knowledge Hub",
  icons: {
    icon: '/favicon.png',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${spaceGrotesk.variable} ${inter.variable} antialiased font-sans`}
      >
        <AuthProvider>
          <ScrollProvider>
            <Navigation />
            <div className="">{children}</div>
          </ScrollProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
