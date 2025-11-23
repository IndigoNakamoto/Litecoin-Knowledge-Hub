import React from 'react'
import Link from 'next/link'

export default function ContributorsPage() {
  return (
    <div className="container">
      <div className="hero">
        <h1>For Contributors</h1>
        <p>
          Help build the Litecoin Knowledge Hub by contributing articles, documentation, and educational content.
        </p>
      </div>

      <div className="section">
        <div className="card">
          <h2>Getting Started</h2>
          <p>
            Contributing to the Litecoin Knowledge Hub is a great way to share your knowledge and help 
            the community grow. Whether you&apos;re an expert developer, educator, or enthusiast, your 
            contributions are valuable.
          </p>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>How to Contribute</h2>
          <ol style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li>
              <strong>Create an Account:</strong> Sign up for access to the CMS admin panel
            </li>
            <li>
              <strong>Review Guidelines:</strong> Familiarize yourself with our content guidelines and standards
            </li>
            <li>
              <strong>Submit Content:</strong> Use the admin panel to create and submit your articles
            </li>
            <li>
              <strong>Review Process:</strong> Your content will be reviewed by our editorial team
            </li>
            <li>
              <strong>Publication:</strong> Once approved, your content will be published to the Knowledge Hub
            </li>
          </ol>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Content Types</h2>
          <div className="grid grid-2" style={{ marginTop: '1.5rem' }}>
            <div>
              <h3>Articles</h3>
              <p>
                In-depth articles covering Litecoin technology, use cases, tutorials, and more.
              </p>
            </div>
            <div>
              <h3>Documentation</h3>
              <p>
                Technical documentation, API references, and developer guides.
              </p>
            </div>
            <div>
              <h3>Tutorials</h3>
              <p>
                Step-by-step guides and tutorials for users and developers.
              </p>
            </div>
            <div>
              <h3>Educational Content</h3>
              <p>
                Educational materials explaining Litecoin concepts and best practices.
              </p>
            </div>
          </div>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Structuring Articles for LLM Processing</h2>
          <p style={{ marginBottom: '1.5rem' }}>
            Well-structured articles are easier for LLMs to process, understand, and adapt. Follow this 
            structure to maximize compatibility with AI-assisted workflows.
          </p>

          <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>Recommended Article Structure</h3>
          <ol style={{ paddingLeft: '1.5rem', lineHeight: '2', marginBottom: '1.5rem' }}>
            <li>
              <strong>Title & Metadata:</strong> Clear, descriptive title with relevant tags and categories
            </li>
            <li>
              <strong>Introduction (H2):</strong> Brief overview of the topic and what readers will learn
            </li>
            <li>
              <strong>Main Sections (H2):</strong> Break content into logical sections with descriptive headings
              <ul style={{ paddingLeft: '1.5rem', marginTop: '0.5rem' }}>
                <li>Use H3 for subsections within main sections</li>
                <li>Keep sections focused on a single topic</li>
                <li>Use consistent heading hierarchy</li>
              </ul>
            </li>
            <li>
              <strong>Code Examples:</strong> Use proper markdown code blocks with language identifiers
            </li>
            <li>
              <strong>Conclusion (H2):</strong> Summarize key points and provide next steps or related resources
            </li>
            <li>
              <strong>References:</strong> List sources, links, and additional reading materials
            </li>
          </ol>

          <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>Markdown Best Practices</h3>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li>Use proper heading hierarchy (H1 → H2 → H3) - never skip levels</li>
            <li>Format code blocks with language identifiers: <code>```python</code> or <code>```javascript</code></li>
            <li>Use lists for better readability and LLM parsing</li>
            <li>Include alt text for images: <code>![description](url)</code></li>
            <li>Use links to reference related content and external resources</li>
            <li>Format tables properly for data presentation</li>
            <li>Use blockquotes for important notes or callouts</li>
          </ul>
        </div>

        <div className="card" style={{ marginTop: '2rem' }}>
          <h2>Best Practices for Using LLMs</h2>
          <p style={{ marginBottom: '1.5rem' }}>
            When using Large Language Models (LLMs) to help create or adapt content, follow these guidelines 
            to ensure high-quality, accurate, and well-structured articles.
          </p>

          <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>Article Structure</h3>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2', marginBottom: '1.5rem' }}>
            <li>
              <strong>Clear Hierarchy:</strong> Use proper heading levels (H1 → H2 → H3) to create a logical 
              document structure that LLMs can parse effectively
            </li>
            <li>
              <strong>Introduction:</strong> Start with a clear introduction that sets context and outlines 
              what readers will learn
            </li>
            <li>
              <strong>Sectioned Content:</strong> Break content into digestible sections with descriptive headings
            </li>
            <li>
              <strong>Conclusion:</strong> End with a summary or actionable next steps
            </li>
            <li>
              <strong>Metadata:</strong> Include proper frontmatter with title, description, tags, and categories
            </li>
          </ul>

          <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>Adapting Articles with LLMs</h3>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2', marginBottom: '1.5rem' }}>
            <li>
              <strong>Review and Edit:</strong> Always review LLM-generated content for accuracy, especially 
              technical details and Litecoin-specific information
            </li>
            <li>
              <strong>Fact-Check:</strong> Verify all technical claims, statistics, and references against 
              official Litecoin documentation
            </li>
            <li>
              <strong>Maintain Voice:</strong> Adapt the tone to match the Knowledge Hub&apos;s style guide 
              and community standards
            </li>
            <li>
              <strong>Add Context:</strong> Enhance LLM output with real-world examples, code snippets, and 
              practical use cases
            </li>
            <li>
              <strong>Update References:</strong> Ensure all links, citations, and external references are 
              current and relevant
            </li>
            <li>
              <strong>Test Code Examples:</strong> If including code, test all examples to ensure they work 
              correctly
            </li>
          </ul>

          <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>Prompt Engineering Tips</h3>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2', marginBottom: '1.5rem' }}>
            <li>
              <strong>Be Specific:</strong> Provide clear instructions about the target audience, tone, and 
              technical level
            </li>
            <li>
              <strong>Provide Context:</strong> Include relevant background information about Litecoin and 
              the specific topic
            </li>
            <li>
              <strong>Request Structure:</strong> Ask for specific formatting, such as markdown, code blocks, 
              or bullet points
            </li>
            <li>
              <strong>Iterate:</strong> Use follow-up prompts to refine and improve the content
            </li>
            <li>
              <strong>Specify Length:</strong> Indicate desired article length or word count
            </li>
          </ul>

          <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>Quality Assurance</h3>
          <ul style={{ paddingLeft: '1.5rem', lineHeight: '2' }}>
            <li>Write clear, concise, and well-structured content</li>
            <li>Include relevant examples and code snippets where applicable</li>
            <li>Use proper formatting and markdown syntax</li>
            <li>Cite sources and provide references when needed</li>
            <li>Ensure accuracy and fact-check your content</li>
            <li>Follow the Litecoin community guidelines</li>
            <li>Proofread for grammar, spelling, and clarity</li>
            <li>Verify all technical information is current and accurate</li>
          </ul>
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

