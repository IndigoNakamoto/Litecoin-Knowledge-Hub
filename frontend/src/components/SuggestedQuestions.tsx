"use client";

import React, { useState, useEffect } from "react";

interface SuggestedQuestionsProps {
  onQuestionClick: (question: string) => void;
}

interface SuggestedQuestion {
  id: string;
  question: string;
  order: number;
  isActive: boolean;
}

interface PayloadResponse {
  docs: SuggestedQuestion[];
  totalDocs: number;
  limit: number;
  totalPages: number;
  page: number;
  pagingCounter: number;
  hasPrevPage: boolean;
  hasNextPage: boolean;
  prevPage: number | null;
  nextPage: number | null;
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({ onQuestionClick }) => {
  const [questions, setQuestions] = useState<SuggestedQuestion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Get Payload CMS URL from environment variable, default to localhost:3001 for development
        const payloadUrl = process.env.NEXT_PUBLIC_PAYLOAD_URL || "http://localhost:3001";
        
        // Build query parameters - Payload uses JSON-based where clauses
        const queryParams = new URLSearchParams({
          where: JSON.stringify({
            isActive: {
              equals: true
            }
          }),
          sort: 'order',
          limit: '100'
        });
        
        // Fetch active questions, sorted by order
        const response = await fetch(
          `${payloadUrl}/api/suggested-questions?${queryParams.toString()}`
        );

        if (!response.ok) {
          const errorText = await response.text();
          let errorMessage = `Failed to fetch questions: ${response.status}`;
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.message || errorJson.errors?.[0]?.message || errorMessage;
          } catch {
            // If response isn't JSON, use the text or status
            errorMessage = errorText || errorMessage;
          }
          console.error("API Error:", {
            status: response.status,
            statusText: response.statusText,
            url: response.url,
            error: errorText
          });
          throw new Error(errorMessage);
        }

        const data: PayloadResponse = await response.json();
        
        // Sort by order (ascending) as a fallback
        const sortedQuestions = data.docs.sort((a, b) => a.order - b.order);
        setQuestions(sortedQuestions);
      } catch (err) {
        console.error("Error fetching suggested questions:", err);
        const errorMessage = err instanceof Error ? err.message : "Failed to load suggested questions";
        setError(errorMessage);
        // Fallback to default questions if API fails
        setQuestions([
          { id: "1", question: "What is Litecoin and how does it differ from Bitcoin?", order: 0, isActive: true },
          { id: "2", question: "How do I buy Litecoin?", order: 1, isActive: true },
          { id: "3", question: "What are the benefits of Litecoin's faster transactions?", order: 2, isActive: true },
          { id: "4", question: "How does Litecoin mining work?", order: 3, isActive: true },
          { id: "5", question: "Does Litecoin have privacy features?", order: 4, isActive: true },
          { id: "6", question: "What are the scalability solutions for Litecoin?", order: 5, isActive: true },
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchQuestions();
  }, []);

  if (isLoading) {
    return (
      <div className="w-full max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-semibold text-foreground mb-2">Get started with Litecoin</h2>
          <p className="text-lg text-muted-foreground">Loading questions...</p>
        </div>
      </div>
    );
  }

  if (questions.length === 0 && !error) {
    return (
      <div className="w-full max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-semibold text-foreground mb-2">Get started with Litecoin</h2>
          <p className="text-lg text-muted-foreground">No suggested questions available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-8">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-semibold text-foreground mb-2">Get started with Litecoin</h2>
        <p className="text-lg text-muted-foreground">Choose a question below or ask your own</p>
        {error && (
          <p className="text-sm text-destructive mt-2">{error}</p>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {questions.map((item) => (
          <button
            key={item.id}
            onClick={() => onQuestionClick(item.question)}
            className="p-4 text-left bg-card border border-border rounded-lg hover:bg-accent hover:border-accent-foreground/20 transition-colors duration-200 group"
          >
            <span className="text-lg text-card-foreground group-hover:text-accent-foreground leading-relaxed">
              {item.question}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedQuestions;
