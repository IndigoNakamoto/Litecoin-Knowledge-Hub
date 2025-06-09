"use client";

import { useState } from "react";
import ChatWindow from "@/components/ChatWindow";
import Message from "@/components/Message";
import InputBox from "@/components/InputBox";

interface Message {
  role: "human" | "ai"; // Changed to match backend Pydantic model
  content: string;
  sources?: { metadata?: { title?: string; source?: string } }[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (message: string) => {
    const newUserMessage: Message = { role: "human", content: message }; // Changed to "human"
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    setIsLoading(true);

    // Prepare chat history for the backend
    // The backend expects a list of {role: "human" | "ai", content: "..."}
    // We need to exclude the *current* user message from the history sent to the backend,
    // as it's part of the 'query' itself.
    const chatHistoryForBackend = messages.map(msg => ({
      role: msg.role, // Already "human" or "ai"
      content: msg.content
    }));

    try {
      const response = await fetch("http://localhost:8000/api/v1/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: message, chat_history: chatHistoryForBackend }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const newAssistantMessage: Message = {
        role: "ai", // Changed to "ai"
        content: data.answer,
        sources: data.sources,
      };
      setMessages((prevMessages) => [...prevMessages, newAssistantMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage: Message = {
        role: "ai", // Changed to "ai"
        content: "Sorry, something went wrong. Please try again.",
      };
      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-h-screen bg-background">
      <div className="flex-1 overflow-hidden">
        <ChatWindow>
          {messages.map((msg, index) => (
            <Message key={index} role={msg.role === "human" ? "user" : "assistant"} content={msg.content} sources={msg.sources} />
          ))}
        </ChatWindow>
      </div>
      <InputBox onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}
