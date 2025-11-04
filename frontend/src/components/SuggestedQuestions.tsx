import React from "react";

interface SuggestedQuestionsProps {
  onQuestionClick: (question: string) => void;
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({ onQuestionClick }) => {
  const questions = [
    "What is Litecoin and how does it differ from Bitcoin?",
    "How do I buy Litecoin?",
    "What are the benefits of Litecoin's faster transactions?",
    "How does Litecoin mining work?"
  ];

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-8">
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold text-foreground mb-2">Get started with Litecoin</h2>
        <p className="text-md text-muted-foreground">Choose a question below or ask your own</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {questions.map((question, index) => (
          <button
            key={index}
            onClick={() => onQuestionClick(question)}
            className="p-4 text-left bg-card border border-border rounded-lg hover:bg-accent hover:border-accent-foreground/20 transition-colors duration-200 group"
          >
            <span className="text-md text-card-foreground group-hover:text-accent-foreground leading-relaxed">
              {question}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedQuestions;
