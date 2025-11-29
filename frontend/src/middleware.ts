import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Middleware to redirect HTTP requests to HTTPS in production.
 * 
 * This provides defense-in-depth when behind a reverse proxy (e.g., Cloudflare Tunnel).
 * Cloudflare should handle the primary redirect, but this ensures redirects even if
 * Cloudflare configuration is misconfigured.
 * 
 * Only runs in production environment.
 */
export function middleware(request: NextRequest) {
  // Only redirect in production
  const isProduction = process.env.NODE_ENV === 'production'
  
  if (!isProduction) {
    return NextResponse.next()
  }
  
  // Check if request is HTTP (via X-Forwarded-Proto header from reverse proxy)
  // Cloudflare Tunnel sets this header
  const forwardedProto = request.headers.get('x-forwarded-proto')?.toLowerCase()
  const url = request.nextUrl.clone()
  
  // If X-Forwarded-Proto indicates HTTP, redirect to HTTPS
  if (forwardedProto === 'http') {
    url.protocol = 'https:'
    
    // Use Host header if available (for proper hostname in redirect)
    // This handles cases where nextUrl.hostname might be 0.0.0.0 (bind address)
    const hostHeader = request.headers.get('host')
    if (hostHeader) {
      // Preserve port if present in Host header
      url.host = hostHeader
    }
    
    return NextResponse.redirect(url, 301)
  }
  
  // Request is already HTTPS, proceed normally
  return NextResponse.next()
}

// Configure which routes this middleware applies to
// Apply to all routes except static files and API routes (which are handled by backend)
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes - handled by backend)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (public folder)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)).*)',
  ],
}

