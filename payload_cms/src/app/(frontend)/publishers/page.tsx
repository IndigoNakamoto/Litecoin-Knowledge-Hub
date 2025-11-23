import React from 'react'
import Link from 'next/link'

export default function PublishersPage() {
  return (
    <div className="container">
      <div className="hero">
        <h1>For Publishers</h1>
        <p>
          Guidelines and resources for publishers looking to share content through the Litecoin Knowledge Hub.
        </p>
      </div>

      <div className="section">
        <div className="card">
          <h2>Publishing Guidelines</h2>
          <p>
            The Litecoin Knowledge Hub welcomes quality content from publishers who want to share 
            valuable information with the Litecoin community. Our platform provides a space for 
            educational, technical, and informative content.
          </p>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Publishing Process</h2>
          <ol style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li>
              <strong>Content Submission:</strong> Submit your content through the CMS admin panel
            </li>
            <li>
              <strong>Editorial Review:</strong> Our team reviews submissions for quality and accuracy
            </li>
            <li>
              <strong>Feedback & Revisions:</strong> We may request revisions to ensure content meets our standards
            </li>
            <li>
              <strong>Approval:</strong> Once approved, content is scheduled for publication
            </li>
            <li>
              <strong>Publication:</strong> Your content goes live on the Knowledge Hub
            </li>
          </ol>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Content Standards</h2>
          <div className="grid grid-2" style={{ marginTop: '1.5rem' }}>
            <div>
              <h3>Quality Requirements</h3>
              <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
                <li>Well-researched and accurate</li>
                <li>Clear and engaging writing</li>
                <li>Proper grammar and spelling</li>
                <li>Relevant to Litecoin community</li>
              </ul>
            </div>
            <div>
              <h3>Formatting Standards</h3>
              <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
                <li>Proper markdown formatting</li>
                <li>Clear headings and structure</li>
                <li>Appropriate use of images</li>
                <li>Code blocks with syntax highlighting</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>What We Publish</h2>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li>Technical articles and tutorials</li>
            <li>Educational content and guides</li>
            <li>Developer documentation</li>
            <li>Community news and updates</li>
            <li>Best practices and case studies</li>
            <li>Research and analysis</li>
          </ul>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>What We Don't Publish</h2>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li>Promotional or advertising content</li>
            <li>Misleading or inaccurate information</li>
            <li>Content that violates community guidelines</li>
            <li>Plagiarized or unoriginal content</li>
            <li>Content with poor quality or formatting</li>
          </ul>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Rights and Attribution</h2>
          <p>
            By publishing content on the Litecoin Knowledge Hub, you grant us the right to host, 
            display, and distribute your content. You retain ownership of your content and will 
            be properly attributed as the author.
          </p>
        </div>

        <div style={{ marginTop: '3rem', textAlign: 'center' }}>
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

