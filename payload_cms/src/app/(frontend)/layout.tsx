import React from 'react'
import './globals.css'
import Navigation from '@/components/Navigation'

export const metadata = {
  description: 'Litecoin Knowledge Hub - Contribute, Publish, and Learn',
  title: 'Litecoin Knowledge Hub',
}

export default async function RootLayout(props: { children: React.ReactNode }) {
  const { children } = props

  return (
    <html lang="en">
      <body>
        <Navigation />
        <main className="main-content">{children}</main>
      </body>
    </html>
  )
}
