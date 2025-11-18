import Navigation from '@/components/Navigation';
import { AuthProvider } from '@/contexts/AuthContext';
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
  title: "Litecoin Knowledge Hub",
  description: "Litecoin Knowledge Hub",
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
          <Navigation />
          <div className="">{children}</div>
        </AuthProvider>
      </body>
    </html>
  );
}
