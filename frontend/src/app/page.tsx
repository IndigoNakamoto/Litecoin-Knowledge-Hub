"use client";

import { useState, useRef, useEffect } from "react";
import ChatWindow, { ChatWindowRef } from "@/components/ChatWindow";
import Message from "@/components/Message";
import StreamingMessage from "@/components/StreamingMessage";
import MessageLoader from "@/components/MessageLoader";
import InputBox from "@/components/InputBox";
import SuggestedQuestions from "@/components/SuggestedQuestions";

interface Message {
  role: "human" | "ai"; // Changed to match backend Pydantic model
  content: string;
  sources?: { metadata?: { title?: string; source?: string } }[];
  status?: "thinking" | "streaming" | "complete" | "error";
  isStreamActive?: boolean;
  id?: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<Message | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const chatWindowRef = useRef<ChatWindowRef>(null);
  const lastUserMessageIdRef = useRef<string | null>(null);

  const handleSendMessage = async (message: string) => {
    const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newUserMessage: Message = { role: "human", content: message, id: messageId };

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
      const response = await fetch(`${backendUrl}/api/v1/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: message, chat_history: chatHistoryForBackend }),
      });

      if (!response.ok) {
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

      // Helper function to process a single SSE data object
      const processData = async (data: any) => {
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
                  // Log the problematic JSON string for debugging
                  const jsonStr = line.slice(6).trim();
                  console.error('Error parsing SSE data:', parseError);
                  console.error('Problematic JSON string:', jsonStr.substring(0, 100));
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
      // Use multiple requestAnimationFrame to ensure DOM is fully updated
      const scrollToMessage = () => {
        const messageElement = document.getElementById(lastUserMessageIdRef.current!);
        if (messageElement && chatWindowRef.current) {
          chatWindowRef.current.scrollToElement(messageElement);
          // Clear the ref after scrolling to prevent re-scrolling
          lastUserMessageIdRef.current = null;
        }
      };
      
      // Wait for React to render and DOM to update
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setTimeout(scrollToMessage, 10); // Small delay to ensure layout is complete
        });
      });
    }
  }, [messages]); // Trigger when messages array changes

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
    <div className="flex flex-col h-screen max-h-screen bg-background">
      <div className="flex-1">
        {messages.length === 0 && !streamingMessage && !isLoading ? (
          <div className="flex items-center justify-center h-full">
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
          </ChatWindow>
        )}
      </div>
      <InputBox onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}
