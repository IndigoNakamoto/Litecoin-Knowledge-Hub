/**
 * Normalizes markdown content to ensure proper rendering.
 * 
 * Fixes common LLM output issues where markdown headings lack proper
 * newlines before them (e.g., "text.## Heading" instead of "text.\n\n## Heading")
 */
export function normalizeMarkdown(content: string): string {
  if (!content) return content;
  
  return content
    // Add newlines before headings that don't have them (h1-h6)
    // Match: any non-whitespace, non-newline, non-# char followed by 1-6 # chars + space
    // The [^\s\n#] excludes # to avoid breaking multi-hash headings like ##
    .replace(/([^\s\n#])(#{1,6}\s)/g, '$1\n\n$2')
    // Clean up any excessive newlines (more than 2 consecutive)
    .replace(/\n{3,}/g, '\n\n');
}

