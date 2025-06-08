"use client";

import { useState } from "react";
import ChatWindow from "@/components/ChatWindow";
import Message from "@/components/Message";
import InputBox from "@/components/InputBox";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: { metadata?: { title?: string; source?: string } }[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (message: string) => {
    const newUserMessage: Message = { role: "user", content: message };
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/v1/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: message }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const newAssistantMessage: Message = {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
      };
      setMessages((prevMessages) => [...prevMessages, newAssistantMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage: Message = {
        role: "assistant",
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
            <Message key={index} role={msg.role} content={msg.content} sources={msg.sources} />
          ))}
        </ChatWindow>
      </div>
      <InputBox onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}
