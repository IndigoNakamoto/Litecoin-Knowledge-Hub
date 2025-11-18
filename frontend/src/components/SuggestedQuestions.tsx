"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768); // md breakpoint in Tailwind
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  return isMobile;
};

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

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({ onQuestionClick, onQuestionsLoaded }) => {
  const [questions, setQuestions] = useState<SuggestedQuestion[]>([]);
  const [allQuestions, setAllQuestions] = useState<SuggestedQuestion[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isMobile = useIsMobile();

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Get Payload CMS URL from environment variable, default to localhost:3001 for development
        const payloadUrl = process.env.NEXT_PUBLIC_PAYLOAD_URL || "https://cms.lite.space";
        
        // Fetch active questions for display
        const activeQueryParams = new URLSearchParams({
          where: JSON.stringify({
            isActive: {
              equals: true
            }
          }),
          sort: 'order',
          limit: '100'
        });
        
        const activeResponse = await fetch(
          `${payloadUrl}/api/suggested-questions?${activeQueryParams.toString()}`
        );

        // Fetch all questions (active + inactive) for "I'm Feeling Lit" random selection
        const allQueryParams = new URLSearchParams({
          sort: 'order',
          limit: '100'
        });
        
        const allResponse = await fetch(
          `${payloadUrl}/api/suggested-questions?${allQueryParams.toString()}`
        );

        if (!activeResponse.ok) {
          const errorText = await activeResponse.text();
          let errorMessage = `Failed to fetch questions: ${activeResponse.status}`;
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.message || errorJson.errors?.[0]?.message || errorMessage;
          } catch {
            // If response isn't JSON, use the text or status
            errorMessage = errorText || errorMessage;
          }
          console.error("API Error:", {
            status: activeResponse.status,
            statusText: activeResponse.statusText,
            url: activeResponse.url,
            error: errorText
          });
          throw new Error(errorMessage);
        }

        const activeData: PayloadResponse = await activeResponse.json();
        
        // Sort by order (ascending) as a fallback
        const sortedActiveQuestions = activeData.docs.sort((a, b) => a.order - b.order);
        setQuestions(sortedActiveQuestions);

        // Also fetch all questions for random selection
        if (allResponse.ok) {
          const allData: PayloadResponse = await allResponse.json();
          const sortedAllQuestions = allData.docs.sort((a, b) => a.order - b.order);
          setAllQuestions(sortedAllQuestions);
          // Notify parent component about loaded questions for finding similar ones
          if (onQuestionsLoaded) {
            onQuestionsLoaded(sortedAllQuestions);
          }
        } else {
          // If all questions fetch fails, use active questions as fallback
          setAllQuestions(sortedActiveQuestions);
          if (onQuestionsLoaded) {
            onQuestionsLoaded(sortedActiveQuestions);
          }
        }
      } catch (err) {
        console.error("Error fetching suggested questions:", err);
        const errorMessage = err instanceof Error ? err.message : "Failed to load suggested questions";
        setError(errorMessage);
        // Fallback to default questions if API fails
        const fallbackQuestions = [
          { id: "1", question: "What is Litecoin and how does it differ from Bitcoin?", order: 0, isActive: true },
          { id: "2", question: "How do I buy Litecoin?", order: 1, isActive: true },
          { id: "3", question: "What are the benefits of Litecoin's faster transactions?", order: 2, isActive: true },
          { id: "4", question: "How does Litecoin mining work?", order: 3, isActive: true },
          { id: "5", question: "Does Litecoin have privacy features?", order: 4, isActive: true },
          { id: "6", question: "What are the scalability solutions for Litecoin?", order: 5, isActive: true },
        ];
        setQuestions(fallbackQuestions);
        setAllQuestions(fallbackQuestions);
        if (onQuestionsLoaded) {
          onQuestionsLoaded(fallbackQuestions);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchQuestions();
  }, [onQuestionsLoaded]);

  if (isLoading) {
    return (
      <div className="w-full max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-6">
          <h2 className="font-space-grotesk text-[30px] font-semibold text-foreground mb-2">Get started with Litecoin</h2>
          <p className="text-lg text-muted-foreground">Loading questions...</p>
        </div>
      </div>
    );
  }

  if (questions.length === 0 && !error) {
    return (
      <div className="w-full max-w-4xl mx-auto px-4 py-8">
        <div className="text-center mb-6">
          <h2 className="font-space-grotesk text-[30px] font-semibold text-foreground mb-2">Get started with Litecoin</h2>
          <p className="text-lg text-muted-foreground">No suggested questions available</p>
        </div>
      </div>
    );
  }

  const handleShowMore = () => {
    setCurrentPage((prev) => prev + 1);
  };

  const handleFeelingLit = () => {
    if (allQuestions.length === 0) return;
    const randomIndex = Math.floor(Math.random() * allQuestions.length);
    const randomQuestion = allQuestions[randomIndex];
    onQuestionClick(randomQuestion.question, { 
      fromFeelingLit: true, 
      originalQuestion: randomQuestion.question 
    });
  };

  const QUESTIONS_PER_PAGE = isMobile ? 3 : 7;
  const startIndex = currentPage * QUESTIONS_PER_PAGE;
  const endIndex = startIndex + QUESTIONS_PER_PAGE;
  const visibleQuestions = questions.slice(startIndex, endIndex);
  const hasMoreQuestions = endIndex < questions.length;

  // Animation variants for questions
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.3,
        ease: [0.4, 0, 0.2, 1] as const,
      },
    },
    exit: {
      opacity: 0,
      y: -10,
      transition: {
        duration: 0.2,
      },
    },
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-8">
      <div className="text-center mb-6">
        <h2 className="font-space-grotesk text-[30px] font-semibold text-foreground mb-2">Get started with Litecoin</h2>
        <p className="text-lg text-muted-foreground">Choose a question below or ask your own</p>
        {error && (
          <p className="text-sm text-destructive mt-2">{error}</p>
        )}
      </div>
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 gap-3 auto-rows-fr"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <AnimatePresence mode="popLayout">
          {visibleQuestions.map((item) => (
            <motion.div
              key={item.id}
              variants={itemVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              layout
              className="flex"
            >
              <button
                onClick={() => onQuestionClick(item.question)}
                className="p-4 text-left bg-card border border-border rounded-lg hover:bg-accent hover:border-accent-foreground/20 transition-colors duration-200 group w-full h-full flex items-center"
              >
                <span className="text-lg text-card-foreground group-hover:text-accent-foreground leading-relaxed">
                  {item.question}
                </span>
              </button>
            </motion.div>
          ))}
          {hasMoreQuestions && (
            <motion.div
              key="show-more"
              variants={itemVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              layout
              className="flex"
            >
              <button
                onClick={handleShowMore}
                className="p-4 text-center bg-card border border-ring/30 rounded-lg hover:bg-accent hover:border-ring/50 transition-colors duration-200 group w-full h-full flex items-center justify-center"
              >
                <span className="text-lg text-card-foreground group-hover:text-accent-foreground leading-relaxed">
                  Show me more
                </span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
      {allQuestions.length > 0 && (
        <motion.div
          className="mt-6 flex justify-center"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.3 }}
        >
          <button
            onClick={handleFeelingLit}
            className="p-4 text-center bg-card border border-ring/30 rounded-lg hover:bg-accent hover:border-ring/50 transition-colors duration-200 group max-w-md w-full"
          >
            <span className="text-lg text-card-foreground group-hover:text-accent-foreground leading-relaxed">
              I&apos;m Feeling Lit
            </span>
          </button>
        </motion.div>
      )}
    </div>
  );
};

export default SuggestedQuestions;
