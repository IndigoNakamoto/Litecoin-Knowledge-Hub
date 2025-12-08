/**
 * Common LaTeX symbols and their Unicode equivalents.
 * Used to convert LLM-generated LaTeX to renderable Unicode.
 */
const LATEX_SYMBOLS: Record<string, string> = {
  // Arrows
  '\\rightarrow': '→',
  '\\leftarrow': '←',
  '\\leftrightarrow': '↔',
  '\\Rightarrow': '⇒',
  '\\Leftarrow': '⇐',
  '\\Leftrightarrow': '⇔',
  '\\uparrow': '↑',
  '\\downarrow': '↓',
  '\\to': '→',
  // Math operators
  '\\times': '×',
  '\\div': '÷',
  '\\pm': '±',
  '\\mp': '∓',
  '\\cdot': '·',
  // Comparison
  '\\neq': '≠',
  '\\leq': '≤',
  '\\geq': '≥',
  '\\approx': '≈',
  '\\equiv': '≡',
  '\\sim': '∼',
  // Greek letters (common)
  '\\alpha': 'α',
  '\\beta': 'β',
  '\\gamma': 'γ',
  '\\delta': 'δ',
  '\\epsilon': 'ε',
  '\\lambda': 'λ',
  '\\mu': 'μ',
  '\\pi': 'π',
  '\\sigma': 'σ',
  '\\omega': 'ω',
  // Other symbols
  '\\infty': '∞',
  '\\degree': '°',
  '\\checkmark': '✓',
  '\\bullet': '•',
};

/**
 * Normalizes markdown content to ensure proper rendering.
 * 
 * Fixes common LLM output issues:
 * - Missing newlines before headings (e.g., "text.## Heading")
 * - Missing newlines before numbered/bulleted lists (e.g., "text:1. Item")
 * - LaTeX math notation not supported by ReactMarkdown (e.g., "$\rightarrow$")
 */
export function normalizeMarkdown(content: string): string {
  if (!content) return content;
  
  let result = content;
  
  // Convert LaTeX \text{...} commands - extract the text content
  // Matches patterns like $0.0001 \text{ LTC per kilobyte}$
  result = result.replace(/\$([^$]*?)\\text\{([^}]*)\}([^$]*?)\$/g, '$1$2$3');
  
  // Convert LaTeX symbols wrapped in $ delimiters to Unicode
  // Matches patterns like $\rightarrow$ or $\times$
  for (const [latex, unicode] of Object.entries(LATEX_SYMBOLS)) {
    // Escape special regex characters in the LaTeX command
    const escapedLatex = latex.replace(/\\/g, '\\\\');
    // Match $\command$ pattern (with optional whitespace)
    const pattern = new RegExp(`\\$\\s*${escapedLatex}\\s*\\$`, 'g');
    result = result.replace(pattern, unicode);
  }
  
  // Add newlines before headings that don't have them (h1-h6)
  // Match: any non-whitespace, non-newline, non-# char followed by 1-6 # chars + space
  // The [^\s\n#] excludes # to avoid breaking multi-hash headings like ##
  result = result.replace(/([^\s\n#])(#{1,6}\s)/g, '$1\n\n$2');
  
  // Add newlines before numbered lists that don't have them
  // Match: any non-whitespace, non-newline char followed by a number and period/paren
  // e.g., "text:1. Item" or "text:1) Item"
  result = result.replace(/([^\s\n])(\d+[.)]\s)/g, '$1\n\n$2');
  
  // Add newlines before bullet points that don't have them
  // Match: any non-whitespace, non-newline char followed by * or - and space
  // But not when it's part of bold (**) or code
  result = result.replace(/([^\s\n*-])([*-]\s)(?![*-])/g, '$1\n\n$2');
  
  // Clean up any excessive newlines (more than 2 consecutive)
  result = result.replace(/\n{3,}/g, '\n\n');
  
  return result;
}

