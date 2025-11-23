import { headers as getHeaders } from 'next/headers'
import { getPayload } from 'payload'
import React from 'react'
import Link from 'next/link'

import config from '@/payload.config'

export default async function HomePage() {
  const headers = await getHeaders()
  const payloadConfig = await config
  const payload = await getPayload({ config: payloadConfig })
  const { user } = await payload.auth({ headers })

  return (
    <div className="container">
      <div className="hero">
        <h1>Litecoin Knowledge Hub</h1>
        <p>
          Welcome to the Litecoin Knowledge Hub CMS. Manage content, collaborate with contributors, 
          and publish articles that help the Litecoin community learn and grow.
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link href="/admin" className="btn btn-primary">
            Go to Admin Panel
          </Link>
          <Link href="/contributors" className="btn btn-outline">
            For Contributors
          </Link>
        </div>
      </div>

      <div className="section">
        <div className="grid grid-3">
          <div className="card">
            <h3>For Contributors</h3>
            <p>
              Learn how to contribute articles, documentation, and knowledge to the Litecoin Knowledge Hub. 
              Share your expertise with the community.
            </p>
            <Link href="/contributors" className="btn btn-secondary" style={{ marginTop: '1rem' }}>
              Learn More →
            </Link>
          </div>

          <div className="card">
            <h3>For Publishers</h3>
            <p>
              Guidelines and resources for publishers looking to share content through the Knowledge Hub. 
              Understand our publishing process and standards.
            </p>
            <Link href="/publishers" className="btn btn-secondary" style={{ marginTop: '1rem' }}>
              Learn More →
            </Link>
          </div>

          <div className="card">
            <h3>Tips & Best Practices</h3>
            <p>
              Discover tips, best practices, and guidelines for creating high-quality content that 
              benefits the Litecoin community.
            </p>
            <Link href="/tips" className="btn btn-secondary" style={{ marginTop: '1rem' }}>
              Learn More →
            </Link>
          </div>
        </div>
      </div>

      {user && (
        <div className="section">
          <div className="card" style={{ textAlign: 'center' }}>
            <h3>Welcome back, {user.email}!</h3>
            <p>You&apos;re logged in and ready to manage content.</p>
            <Link href="/admin" className="btn btn-primary" style={{ marginTop: '1rem' }}>
              Open Admin Panel
            </Link>
          </div>
        </div>
      )}

      <footer className="footer">
        <p>Litecoin Knowledge Hub CMS - Powered by the Litecoin Foundation</p>
      </footer>
    </div>
  )
}
