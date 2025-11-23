"use client";

import { useState, useRef, useEffect } from "react";
import ChatWindow, { ChatWindowRef } from "@/components/ChatWindow";
import Message from "@/components/Message";
import StreamingMessage from "@/components/StreamingMessage";
import MessageLoader from "@/components/MessageLoader";
import InputBox from "@/components/InputBox";
import SuggestedQuestions from "@/components/SuggestedQuestions";
import { getFingerprintWithChallenge, getFingerprint } from "@/lib/utils/fingerprint";

interface Message {
  role: "human" | "ai"; // Changed to match backend Pydantic model
  content: string;
  sources?: { metadata?: { title?: string; source?: string } }[];
  status?: "thinking" | "streaming" | "complete" | "error";
  isStreamActive?: boolean;
  id?: string;
}

interface UsageStatus {
  status: string;
  warning_level: "error" | "warning" | "info" | null;
  daily_percentage: number;
  hourly_percentage: number;
  // Note: daily_remaining and hourly_remaining removed for security (cost information)
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<Message | null>(null);
  const [usageWarning, setUsageWarning] = useState<UsageStatus | null>(null);
  // Fingerprint state is kept for background refresh, but we fetch fresh before each request
  const [_fingerprint, setFingerprint] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const chatWindowRef = useRef<ChatWindowRef>(null);
  const lastUserMessageIdRef = useRef<string | null>(null);
  
  // Helper function to ensure we have a fresh challenge and fingerprint
  const ensureFreshFingerprint = async (): Promise<string | null> => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const response = await fetch(`${backendUrl}/api/v1/auth/challenge`);
      
      if (response.ok) {
        const data = await response.json();
        const challengeId = data.challenge;
        
        if (challengeId && challengeId !== "disabled") {
          // Generate fingerprint with challenge
          const fp = await getFingerprintWithChallenge(challengeId);
          setFingerprint(fp);
          return fp;
        } else {
          // Challenge disabled, generate fingerprint without challenge (backward compatibility)
          const fp = await getFingerprint();
          setFingerprint(fp);
          return fp;
        }
      } else if (response.status === 429) {
        // Rate limited - extract error message from response
        try {
          const errorData = await response.json();
          const errorMessage = errorData?.detail?.message || "Rate limited: Too many challenge requests. Please wait a moment and try again.";
          throw new Error(errorMessage);
        } catch {
          // If parsing fails, use default message
          throw new Error("Rate limited: Too many challenge requests. Please wait a moment and try again.");
        }
      } else {
        // Other error - fallback to fingerprint without challenge (backward compatibility)
        console.debug("Challenge fetch failed with status:", response.status);
        const fp = await getFingerprint();
        setFingerprint(fp);
        return fp;
      }
    } catch (error) {
      // If it's a rate limit error, re-throw it
      if (error instanceof Error && error.message.includes("Rate limited")) {
        throw error;
      }
      // Other errors - fallback to fingerprint without challenge (backward compatibility)
      console.debug("Failed to fetch challenge:", error);
      const fp = await getFingerprint();
      setFingerprint(fp);
      return fp;
    }
  };

  const MAX_QUERY_LENGTH = 400;
  
  // Fetch challenge and generate fingerprint on mount
  useEffect(() => {
    const fetchChallengeAndGenerateFingerprint = async () => {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
        const response = await fetch(`${backendUrl}/api/v1/auth/challenge`);
        
        if (response.ok) {
          const data = await response.json();
          const challengeId = data.challenge;
          
          if (challengeId && challengeId !== "disabled") {
            // Generate fingerprint with challenge
            const fp = await getFingerprintWithChallenge(challengeId);
            setFingerprint(fp);
            // Note: No background refresh needed - challenges are fetched on-demand before each request
            // via ensureFreshFingerprint() in handleSendMessage()
          } else {
            // Challenge disabled, generate fingerprint without challenge (backward compatibility)
            const fp = await getFingerprint();
            setFingerprint(fp);
          }
        } else {
          // Challenge fetch failed, generate fingerprint without challenge (backward compatibility)
          const fp = await getFingerprint();
          setFingerprint(fp);
        }
      } catch (error) {
        console.debug("Failed to fetch challenge:", error);
        // Generate fingerprint without challenge (backward compatibility)
        const fp = await getFingerprint();
        setFingerprint(fp);
      }
    };
    
    fetchChallengeAndGenerateFingerprint();
  }, []);

  // Check usage status periodically
  useEffect(() => {
    const checkUsageStatus = async () => {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
        const response = await fetch(`${backendUrl}/api/v1/admin/usage/status`);
        if (response.ok) {
          const status: UsageStatus = await response.json();
          setUsageWarning(status.warning_level ? status : null);
        }
      } catch (error) {
        // Silently fail - don't show errors for usage checks
        console.debug("Failed to check usage status:", error);
      }
    };

    // Check immediately and then every 30 seconds
    checkUsageStatus();
    const interval = setInterval(checkUsageStatus, 30000);

    return () => clearInterval(interval);
  }, []);


  const handleSendMessage = async (message: string, _metadata?: { fromFeelingLit?: boolean; originalQuestion?: string }) => {
    // Validate message length
    if (message.length > MAX_QUERY_LENGTH) {
      alert(`Message is too long. Maximum length is ${MAX_QUERY_LENGTH} characters. Your message is ${message.length} characters.`);
      return;
    }

    // Trim whitespace
    const trimmedMessage = message.trim();
    if (!trimmedMessage) {
      return; // Don't send empty messages
    }

    const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newUserMessage: Message = { role: "human", content: trimmedMessage, id: messageId };

    // Prepare chat history for the backend - only include complete exchanges
    const chatHistoryForBackend = messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    lastUserMessageIdRef.current = messageId;
    setIsLoading(true);

    // Initialize streaming message
    const initialStreamingMessage: Message = {
      role: "ai",
      content: "",
      status: "thinking",
      isStreamActive: true
    };
    setStreamingMessage(initialStreamingMessage);

    try {
      // Close any existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      
      // Ensure we have a fresh challenge and fingerprint before each request
      // Challenges are one-time use, so we need a new one for each request
      let currentFingerprint: string | null;
      try {
        currentFingerprint = await ensureFreshFingerprint();
      } catch (error) {
        // If challenge fetch failed (e.g., rate limited), show error and don't proceed
        if (error instanceof Error && error.message.includes("Rate limited")) {
          setStreamingMessage({
            role: "ai",
            content: error.message,
            status: "error",
            isStreamActive: false,
          });
          setIsLoading(false);
          return;
        }
        // For other errors, fall back to fingerprint without challenge
        currentFingerprint = await getFingerprint();
      }
      
      // Prepare headers with fingerprint if available
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      
      if (currentFingerprint) {
        headers["X-Fingerprint"] = currentFingerprint;
      }
      
      let response = await fetch(`${backendUrl}/api/v1/chat/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify({ query: trimmedMessage, chat_history: chatHistoryForBackend }),
      });

      // Handle HTTP errors explicitly so we can surface clear messages (e.g., rate limiting)
      if (!response.ok) {
        // Handle invalid challenge error - retry once with a fresh challenge
        if (response.status === 403) {
          try {
            const errorBody = await response.json();
            if (errorBody?.detail?.error === "invalid_challenge") {
              // Fetch a new challenge and retry once
              console.debug("Challenge invalid, fetching new challenge and retrying...");
              const newFingerprint = await ensureFreshFingerprint();
              
              if (newFingerprint) {
                headers["X-Fingerprint"] = newFingerprint;
                const retryResponse = await fetch(`${backendUrl}/api/v1/chat/stream`, {
                  method: "POST",
                  headers,
                  body: JSON.stringify({ query: trimmedMessage, chat_history: chatHistoryForBackend }),
                });
                
                if (retryResponse.ok) {
                  // Retry succeeded, replace response with retryResponse and continue
                  // We'll process it in the normal flow below
                  response = retryResponse;
                  // Skip the rest of error handling since retry succeeded
                } else {
                  // Retry also failed, show error
                  const retryErrorBody = await retryResponse.json().catch(() => ({}));
                  const retryMessage = retryErrorBody?.detail?.message || `HTTP error! status: ${retryResponse.status}`;
                  setStreamingMessage({
                    role: "ai",
                    content: retryMessage,
                    status: "error",
                    isStreamActive: false,
                  });
                  setIsLoading(false);
                  return;
                }
              } else {
                // Could not get new fingerprint, show error
                setStreamingMessage({
                  role: "ai",
                  content: errorBody?.detail?.message || "Invalid security challenge. Please refresh the page and try again.",
                  status: "error",
                  isStreamActive: false,
                });
                setIsLoading(false);
                return;
              }
            } else {
              // Other 403 error, show message (errorBody already parsed above)
              setStreamingMessage({
                role: "ai",
                content: errorBody?.detail?.message || "Access forbidden. Please refresh the page and try again.",
                status: "error",
                isStreamActive: false,
              });
              setIsLoading(false);
              return;
            }
          } catch (parseError) {
            // If we can't parse the error, fall through to generic error handling
            console.debug("Could not parse error response:", parseError);
          }
        }
        
        // If response is still not ok after retry handling, continue with other error handling
        if (!response.ok && response.status === 429) {
          let retryAfterSeconds: number | null = null;
          const retryAfterHeader = response.headers.get("Retry-After");
          if (retryAfterHeader) {
            const parsed = parseInt(retryAfterHeader, 10);
            if (!Number.isNaN(parsed)) {
              retryAfterSeconds = parsed;
            }
          }

          let serverMessage: string | null = null;
          try {
            const body = await response.json();
            if (body && body.detail) {
              // Handle both object and string detail formats
              if (typeof body.detail === "object" && typeof body.detail.message === "string") {
                serverMessage = body.detail.message;
              } else if (typeof body.detail === "string") {
                serverMessage = body.detail;
              }
            }
          } catch {
            // Ignore JSON parse errors and fall back to default message
          }

          const humanReadableRetry =
            retryAfterSeconds && retryAfterSeconds >= 60
              ? `${Math.round(retryAfterSeconds / 60)} minute${retryAfterSeconds >= 120 ? "s" : ""}`
              : retryAfterSeconds
              ? `${retryAfterSeconds} seconds`
              : null;

          const content =
            serverMessage ||
            (humanReadableRetry
              ? `You're sending messages too quickly. Please wait about ${humanReadableRetry} and try again.`
              : "You're sending messages too quickly. Please wait a bit and try again.");

          setStreamingMessage({
            role: "ai",
            content,
            status: "error",
            isStreamActive: false,
          });
          setIsLoading(false);
          return;
        }

        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error("Response body is not readable");
      }

      let accumulatedContent = "";
      let sources: { metadata?: { title?: string; source?: string } }[] = [];
      let buffer = ""; // Buffer for incomplete lines
      let shouldBreak = false;

      // Type for SSE data objects
      type SSEData = 
        | { status: 'thinking' }
        | { status: 'sources'; sources?: { metadata?: { title?: string; source?: string } }[] }
        | { status: 'streaming'; chunk: string }
        | { status: 'complete' }
        | { status: 'error'; error?: string };

      // Helper function to process a single SSE data object
      const processData = async (data: SSEData) => {
        if (data.status === 'thinking') {
          setStreamingMessage(prev => prev ? { ...prev, status: 'thinking' } : null);
        } else if (data.status === 'sources') {
          sources = data.sources || [];
          setStreamingMessage(prev => prev ? {
            ...prev,
            sources: sources
          } : null);
        } else if (data.status === 'streaming') {
          // Accumulate characters and display word by word
          let wordBuffer = "";
          for (const char of data.chunk) {
            wordBuffer += char;
            accumulatedContent += char;

            // Check if we've completed a word (space, punctuation, or end of chunk)
            const isWordBoundary = char === ' ' || char === '\n' || char === '.' || char === '!' || char === '?' || char === ',' || char === ';' || char === ':';

            if (isWordBoundary || wordBuffer.length > 20) { // Also break long words
              setStreamingMessage(prev => prev ? {
                ...prev,
                content: accumulatedContent,
                status: 'streaming',
                sources: sources,
                isStreamActive: true
              } : null);
              // Delay between words for natural typing rhythm
              await new Promise(resolve => setTimeout(resolve, 25));
              wordBuffer = "";
            }
          }

          // Display any remaining characters in the buffer
          if (wordBuffer.length > 0) {
            setStreamingMessage(prev => prev ? {
              ...prev,
              content: accumulatedContent,
              status: 'streaming',
              sources: sources,
              isStreamActive: true
            } : null);
          }
        } else if (data.status === 'complete') {
          setStreamingMessage(prev => prev ? {
            ...prev,
            content: accumulatedContent,
            status: 'complete',
            sources: sources,
            isStreamActive: false
          } : null);
          shouldBreak = true;
        } else if (data.status === 'error') {
          setStreamingMessage(prev => prev ? {
            ...prev,
            content: data.error || "An error occurred",
            status: 'error',
            isStreamActive: false
          } : null);
          shouldBreak = true;
        }
      };

      const processStream = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              // Process any remaining buffer content
              if (buffer.trim()) {
                const lines = buffer.split('\n');
                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    try {
                      const jsonStr = line.slice(6).trim();
                      if (!jsonStr) continue;
                      const data = JSON.parse(jsonStr);
                      await processData(data);
                      if (shouldBreak) break;
                    } catch (parseError) {
                      console.error('Error parsing final SSE data:', parseError);
                    }
                  }
                }
              }
              break;
            }

            // Decode chunk and append to buffer
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;

            // Process complete lines (lines ending with \n)
            const lines = buffer.split('\n');
            // Keep the last incomplete line in the buffer
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const jsonStr = line.slice(6).trim();
                  // Skip empty lines
                  if (!jsonStr) continue;
                  
                  const data = JSON.parse(jsonStr);
                  await processData(data);
                  if (shouldBreak) break;
                } catch (parseError) {
                  // Log parse error without exposing potentially sensitive data
                  console.error('Error parsing SSE data:', parseError);
                  // Continue processing other lines instead of breaking
                }
              }
            }
            
            if (shouldBreak) break;
          }
        } catch (error) {
          console.error('Stream processing error:', error);
          setStreamingMessage(prev => prev ? {
            ...prev,
            content: "Sorry, something went wrong. Please try again.",
            status: 'error',
            isStreamActive: false
          } : null);
        }
      };

      await processStream();

    } catch (error) {
      console.error("Error sending message:", error);
      setStreamingMessage({
        role: "ai",
        content: "Sorry, something went wrong. Please try again.",
        status: 'error',
        isStreamActive: false
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Effect to scroll user message to top when it's added
  useEffect(() => {
    // Only scroll if we have a pending user message ID
    if (lastUserMessageIdRef.current && chatWindowRef.current) {
      const messageId = lastUserMessageIdRef.current;
      
      // Function to attempt scrolling
      const attemptScroll = (retryCount = 0) => {
        const messageElement = document.getElementById(messageId);
        if (messageElement && chatWindowRef.current) {
          chatWindowRef.current.scrollToElement(messageElement);
          // Don't clear the ref yet - we'll clear it after streaming message appears
          return true;
        } else if (retryCount < 5) {
          // Retry up to 5 times with increasing delays
          setTimeout(() => attemptScroll(retryCount + 1), 50 * (retryCount + 1));
        }
        return false;
      };
      
      // Try immediate scroll, then with delays
      requestAnimationFrame(() => {
        attemptScroll(0);
      });
    }
  }, [messages]); // Trigger when messages array changes

  // Effect to re-scroll when streaming message appears to ensure proper positioning
  useEffect(() => {
    // Re-scroll to user message when streaming message is set to account for layout changes
    if (lastUserMessageIdRef.current && chatWindowRef.current && streamingMessage) {
      const messageId = lastUserMessageIdRef.current;
      
      const scrollToMessage = () => {
        const messageElement = document.getElementById(messageId);
        if (messageElement && chatWindowRef.current) {
          chatWindowRef.current.scrollToElement(messageElement);
          // Clear the ref after scrolling to prevent re-scrolling
          lastUserMessageIdRef.current = null;
        }
      };
      
      // Wait for streaming message to render, with multiple attempts
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setTimeout(scrollToMessage, 100);
          // Also try again after a longer delay in case layout is still settling
          setTimeout(scrollToMessage, 300);
        });
      });
    }
  }, [streamingMessage]); // Trigger when streaming message changes

  // Effect to move completed streaming message to messages array
  useEffect(() => {
    if (streamingMessage && streamingMessage.status === 'complete') {
      setMessages(prev => [...prev, {
        role: streamingMessage.role,
        content: streamingMessage.content,
        sources: streamingMessage.sources
      }]);
      setStreamingMessage(null);
    } else if (streamingMessage && streamingMessage.status === 'error') {
      setMessages(prev => [...prev, {
        role: streamingMessage.role,
        content: streamingMessage.content,
        sources: streamingMessage.sources
      }]);
      setStreamingMessage(null);
    }
  }, [streamingMessage]);

  return (
    <div className="flex flex-col h-screen max-h-screen bg-background relative z-10">
      {/* Usage Warning Banner */}
      {usageWarning && usageWarning.warning_level && (
        <div
          className={`px-4 py-2 text-sm text-center ${
            usageWarning.warning_level === "error"
              ? "bg-red-100 text-red-800 border-b border-red-200"
              : usageWarning.warning_level === "warning"
              ? "bg-yellow-100 text-yellow-800 border-b border-yellow-200"
              : "bg-blue-100 text-blue-800 border-b border-blue-200"
          }`}
        >
          {usageWarning.warning_level === "error" ? (
            <span>
              ⚠️ Service temporarily unavailable due to high usage. Please try again later.
            </span>
          ) : usageWarning.warning_level === "warning" ? (
            <span>
              ⚠️ High usage detected ({Math.round(Math.max(usageWarning.daily_percentage, usageWarning.hourly_percentage))}% of limit). 
              Service may be limited soon.
            </span>
          ) : (
            <span>
              ℹ️ Usage at {Math.round(Math.max(usageWarning.daily_percentage, usageWarning.hourly_percentage))}% of limit.
            </span>
          )}
        </div>
      )}
      <div className="flex-1 min-h-0 overflow-hidden relative z-10">
        {messages.length === 0 && !streamingMessage && !isLoading ? (
          <div className="flex items-center justify-center h-full relative z-10">
            <SuggestedQuestions onQuestionClick={handleSendMessage} />
          </div>
        ) : (
          <ChatWindow ref={chatWindowRef} shouldScrollToBottom={false}>
            {messages.map((msg, index) => (
              <Message
                key={msg.id || index}
                messageId={msg.id}
                role={msg.role === "human" ? "user" : "assistant"}
                content={msg.content}
                sources={msg.sources}
              />
            ))}
            {streamingMessage && (
              <StreamingMessage
                content={streamingMessage.content}
                status={streamingMessage.status || "thinking"}
                sources={streamingMessage.sources}
                isStreamActive={streamingMessage.isStreamActive || false}
              />
            )}
            {!streamingMessage && isLoading && <MessageLoader />}
            {/* Spacer to provide scrollable space below messages so they can scroll to top */}
            {/* Only show spacer when streaming, loading, or actively scrolling a new message to avoid empty space after completion */}
            {/* Height accounts for header (~80px) and input box (~150px) */}
            {(streamingMessage || isLoading || lastUserMessageIdRef.current) && (
              <div className="min-h-screen" />
            )}
          </ChatWindow>
        )}
      </div>
      <InputBox onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}
