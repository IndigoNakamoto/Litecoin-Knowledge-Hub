import React from 'react'
import Link from 'next/link'

export default function TipsPage() {
  return (
    <div className="container">
      <div className="hero">
        <h1>Tips & Best Practices</h1>
        <p>
          Learn how to create high-quality content that benefits the Litecoin community.
        </p>
      </div>

      <div className="section">
        <div className="card">
          <h2>Writing Tips</h2>
          <div className="grid grid-2" style={{ marginTop: '1.5rem' }}>
            <div>
              <h3>Structure Your Content</h3>
              <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
                <li>Start with a clear introduction</li>
                <li>Use descriptive headings</li>
                <li>Break content into digestible sections</li>
                <li>End with a conclusion or summary</li>
              </ul>
            </div>
            <div>
              <h3>Make It Engaging</h3>
              <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
                <li>Use clear, concise language</li>
                <li>Include relevant examples</li>
                <li>Add visuals when helpful</li>
                <li>Write for your audience</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Technical Writing</h2>
          <div className="grid grid-2" style={{ marginTop: '1.5rem' }}>
            <div>
              <h3>Code Examples</h3>
              <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
                <li>Use proper syntax highlighting</li>
                <li>Include comments in code</li>
                <li>Test all code examples</li>
                <li>Explain what the code does</li>
              </ul>
            </div>
            <div>
              <h3>Documentation</h3>
              <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
                <li>Be thorough and accurate</li>
                <li>Include parameter descriptions</li>
                <li>Provide usage examples</li>
                <li>Keep documentation up to date</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Markdown Best Practices</h2>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li>Use proper heading hierarchy (H1 → H2 → H3)</li>
            <li>Format code blocks with language identifiers</li>
            <li>Use lists for better readability</li>
            <li>Include alt text for images</li>
            <li>Use links to reference related content</li>
            <li>Format tables properly for data presentation</li>
          </ul>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Content Quality Checklist</h2>
          <div style={{ marginTop: '1.5rem' }}>
            <h3>Before Submitting:</h3>
            <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
              <li>✓ Proofread for spelling and grammar errors</li>
              <li>✓ Verify all facts and technical information</li>
              <li>✓ Test all code examples and links</li>
              <li>✓ Ensure proper formatting and structure</li>
              <li>✓ Include relevant images or diagrams</li>
              <li>✓ Add proper metadata and tags</li>
              <li>✓ Review for clarity and readability</li>
            </ul>
          </div>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>SEO and Discoverability</h2>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li>Use descriptive titles and headings</li>
            <li>Include relevant keywords naturally</li>
            <li>Write clear meta descriptions</li>
            <li>Use proper heading tags</li>
            <li>Add alt text to images</li>
            <li>Link to related content</li>
          </ul>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Community Guidelines</h2>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li>Be respectful and inclusive</li>
            <li>Provide accurate information</li>
            <li>Cite sources when appropriate</li>
            <li>Avoid promotional content</li>
            <li>Follow Litecoin community values</li>
            <li>Engage constructively with feedback</li>
          </ul>
        </div>

        <div style={{ marginTop: '3rem', textAlign: 'center' }}>
          <Link href="/contributors" className="btn btn-secondary" style={{ marginRight: '1rem' }}>
            Learn About Contributing
          </Link>
          <Link href="/admin" className="btn btn-primary">
            Access Admin Panel
          </Link>
        </div>
      </div>

      <footer className="footer">
        <p>
          <Link href="/">← Back to Home</Link>
        </p>
      </footer>
    </div>
  )
}

