import Navigation from '@/components/NavigationMain';
import { AuthProvider } from '@/contexts/AuthContext';
import { ScrollProvider } from '@/contexts/ScrollContext';
import type { Metadata } from 'next';
import { Geist, Geist_Mono, Space_Grotesk, Inter } from 'next/font/google';
import type { ReactNode } from 'react';
import './globals.css';

const metadataBase = new URL('https://chat.lite.space');

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
  metadataBase,
  title: 'Litecoin - Chat',
  description: 'Chat with the Litecoin Knowledge Hub—ask questions and get sourced answers about Litecoin.',
  icons: {
    icon: '/favicon.png',
  },
  alternates: {
    canonical: '/',
  },
  openGraph: {
    title: 'Litecoin - Chat',
    description: 'Chat with the Litecoin Knowledge Hub—ask questions and get sourced answers about Litecoin.',
    url: '/',
    siteName: 'Litecoin Chat',
    type: 'website',
    images: [
      {
        url: '/static/og_image.png',
        width: 1200,
        height: 628,
        alt: 'Litecoin Chat',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Litecoin - Chat',
    description: 'Chat with the Litecoin Knowledge Hub—ask questions and get sourced answers about Litecoin.',
    images: ['/static/og_image.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
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
