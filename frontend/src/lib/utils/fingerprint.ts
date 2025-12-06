/**
 * Client-side fingerprint generation utility.
 * 
 * Generates a unique browser fingerprint for rate limiting and abuse prevention.
 * Supports challenge-response fingerprinting by including a server-generated
 * challenge in the fingerprint hash.
 * 
 * Uses stable browser characteristics + session identifier for uniqueness.
 * The session identifier is stored in sessionStorage (works in incognito mode).
 * The base fingerprint is stored in localStorage to ensure consistency across
 * page loads and prevent multiple "unique users" from the same browser.
 */

const FINGERPRINT_STORAGE_KEY = "browser_fingerprint";
const SESSION_ID_KEY = "browser_session_id";

/**
 * Generate a unique session ID that persists during the browser session.
 * Works in incognito mode (sessionStorage persists during session).
 * 
 * @returns Session ID string (UUID v4 format)
 */
function getOrCreateSessionId(): string {
  if (typeof window === "undefined" || !window.sessionStorage) {
    // Fallback: generate a simple ID if sessionStorage is unavailable
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
  }

  let sessionId = sessionStorage.getItem(SESSION_ID_KEY);
  if (!sessionId) {
    // Generate a UUID v4-like identifier
    sessionId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
    try {
      sessionStorage.setItem(SESSION_ID_KEY, sessionId);
    } catch (error) {
      // sessionStorage might be disabled - continue with generated ID
      console.warn("Failed to store session ID in sessionStorage:", error);
    }
  }
  return sessionId;
}

/**
 * Generate a browser fingerprint hash from stable browser characteristics.
 * 
 * Uses only stable characteristics that don't change between page loads:
 * - User agent, language, platform, vendor
 * - Screen resolution (not window size)
 * - Timezone, hardware specs
 * - Device pixel ratio
 * - Touch support
 * - Cookie/storage support
 * - Session ID (unique per browser session)
 * 
 * Does NOT include:
 * - Window dimensions (can change with resizing)
 * - Challenge (handled separately)
 * 
 * @param challenge Optional challenge string to include in the hash (for challenge-response)
 * @returns Fingerprint hash string (32 characters)
 */
export async function generateFingerprintHash(challenge?: string): Promise<string> {
  // Collect stable browser characteristics only
  // Note: window.innerWidth/innerHeight are excluded as they change with window resizing
  const nav = navigator as Navigator & { 
    deviceMemory?: number;
    maxTouchPoints?: number;
    cookieEnabled?: boolean;
    doNotTrack?: string | null;
    vendor?: string;
    vendorSub?: string;
    appCodeName?: string;
    appName?: string;
    appVersion?: string;
    product?: string;
    productSub?: string;
    buildID?: string; // Firefox only
  };

  // Get session ID (unique per browser session, works in incognito)
  const sessionId = getOrCreateSessionId();

  const characteristics: string[] = [
    navigator.userAgent || "",
    navigator.language || "",
    (navigator.languages || []).join(","), // All languages, not just primary
    screen.width.toString(),        // Screen resolution (stable)
    screen.height.toString(),        // Screen resolution (stable)
    screen.colorDepth.toString(),
    screen.pixelDepth.toString(),   // Additional screen property
    screen.availWidth.toString(),   // Available screen width
    screen.availHeight.toString(),   // Available screen height
    (window.devicePixelRatio || 1).toString(), // Device pixel ratio
    new Date().getTimezoneOffset().toString(),
    navigator.hardwareConcurrency?.toString() || "",
    nav.deviceMemory?.toString() || "",
    navigator.platform || "",
    nav.vendor || "",
    nav.vendorSub || "",
    nav.appCodeName || "",
    nav.appName || "",
    nav.appVersion || "",
    nav.product || "",
    nav.productSub || "",
    nav.buildID || "", // Firefox build ID (if available)
    nav.maxTouchPoints?.toString() || "0",
    nav.cookieEnabled ? "1" : "0",
    nav.doNotTrack || "unknown",
    // Session ID provides uniqueness even for identical hardware
    sessionId,
  ];

  // Include challenge if provided (for challenge-response fingerprinting)
  if (challenge) {
    characteristics.push(challenge);
  }

  // Create a combined string
  const combined = characteristics.join("|");

  // Generate hash using SubtleCrypto (Web Crypto API)
  try {
    const encoder = new TextEncoder();
    const data = encoder.encode(combined);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
    
    // Return first 32 characters (128 bits)
    return hashHex.substring(0, 32);
  } catch (error) {
    // Fallback to a simple hash if crypto.subtle is not available
    console.warn("Web Crypto API not available, using fallback hash", error);
    return fallbackHash(combined);
  }
}

/**
 * Fallback hash function for environments without Web Crypto API support.
 * 
 * @param input Input string to hash
 * @returns Hash string (32 characters)
 */
function fallbackHash(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  
  // Convert to positive hex string and pad to 32 characters
  const hashHex = Math.abs(hash).toString(16);
  return hashHex.padStart(32, "0").substring(0, 32);
}

/**
 * Generate a fingerprint with challenge included.
 * 
 * Format: fp:challenge:hash
 * - fp: prefix
 * - challenge: Challenge ID from server
 * - hash: Base fingerprint hash (hash of browser characteristics WITHOUT challenge)
 * 
 * The hash should be the same base hash used when requesting the challenge,
 * not a new hash that includes the challenge. This ensures the backend can
 * match the challenge to the correct identifier.
 * 
 * @param challenge Challenge ID from server
 * @param baseFingerprint Optional base fingerprint hash to reuse (if not provided, generates new base hash)
 * @returns Fingerprint string in format "fp:challenge:hash"
 */
export async function getFingerprintWithChallenge(challenge: string, baseFingerprint?: string): Promise<string> {
  // Use provided base fingerprint or generate new one (without challenge)
  const hash = baseFingerprint || await generateFingerprintHash();
  return `fp:${challenge}:${hash}`;
}

/**
 * Get or generate a persistent browser fingerprint.
 * 
 * The fingerprint is stored in localStorage to ensure consistency across
 * page loads. This prevents the same browser from being counted as multiple
 * unique users.
 * 
 * @returns Fingerprint hash string (32 characters)
 */
export async function getFingerprint(): Promise<string> {
  // Check if we have a stored fingerprint
  if (typeof window !== "undefined" && window.localStorage) {
    const stored = localStorage.getItem(FINGERPRINT_STORAGE_KEY);
    if (stored) {
      return stored;
    }
  }
  
  // Generate new fingerprint (without challenge)
  const fingerprint = await generateFingerprintHash();
  
  // Store it for future use
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      localStorage.setItem(FINGERPRINT_STORAGE_KEY, fingerprint);
    } catch (error) {
      // localStorage might be disabled or full - continue without storing
      console.warn("Failed to store fingerprint in localStorage:", error);
    }
  }
  
  return fingerprint;
}



