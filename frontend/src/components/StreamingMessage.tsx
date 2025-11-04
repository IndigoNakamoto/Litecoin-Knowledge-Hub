import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface StreamingMessageProps {
  content: string;
  status: "thinking" | "streaming" | "complete" | "error";
  sources?: { metadata?: { title?: string; source?: string } }[];
  isStreamActive: boolean;
}

const StreamingMessage: React.FC<StreamingMessageProps> = ({
  content,
  status,
  sources,
  isStreamActive
}) => {
  const [showCursor, setShowCursor] = useState(false);

  // Handle cursor blinking during streaming
  useEffect(() => {
    if (status === "streaming" && isStreamActive) {
      const interval = setInterval(() => {
        setShowCursor(prev => !prev);
      }, 500);
      return () => clearInterval(interval);
    } else {
      setShowCursor(false);
    }
  }, [status, isStreamActive]);

  const getStatusText = () => {
    switch (status) {
      case "thinking":
        return "";
      case "streaming":
        return "";
      case "complete":
        return "";
      case "error":
        return "Error occurred";
      default:
        return "";
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case "thinking":
        return "text-blue-500";
      case "streaming":
        return "text-green-500";
      case "error":
        return "text-red-500";
      default:
        return "text-muted-foreground";
    }
  };

  return (
    <div className="w-full">
      {/* Status indicator */}
      {status !== "complete" && (
        <div className={`text-xs ${getStatusColor()} flex items-center gap-2 mb-2 mx-auto`}>
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"></div>
          </div>
          {getStatusText()}
        </div>
      )}

      {/* Message content */}
      <div className="prose prose-lg max-w-none dark:prose-invert prose-p:my-8 prose-headings:my-2 text-lg">
        <div className="animate-fade-in">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <h1 className="text-xl font-semibold mt-4 mb-2 text-foreground">{children}</h1>,
              h2: ({ children }) => <h2 className="text-lg font-semibold mt-3 mb-2 text-foreground">{children}</h2>,
              h3: ({ children }) => <h3 className="text-base font-semibold mt-2 mb-1 text-foreground">{children}</h3>,
              h4: ({ children }) => <h4 className="text-sm font-semibold mt-2 mb-1 text-foreground">{children}</h4>,
              h5: ({ children }) => <h5 className="text-sm font-medium mt-1 mb-1 text-foreground">{children}</h5>,
              h6: ({ children }) => <h6 className="text-sm font-medium mt-1 mb-1 text-foreground">{children}</h6>,
            }}
          >
            {content + (showCursor ? "▊" : "")}
          </ReactMarkdown>
        </div>
      </div>

      {/* Sources */}
      {sources && sources.length > 0 && status === "complete" && (
        <Accordion type="single" collapsible className="w-full mt-4">
          <AccordionItem value="sources">
            <AccordionTrigger className="text-sm">Sources</AccordionTrigger>
            <AccordionContent>
              <ul className="list-disc pl-5 text-xs">
                {sources.map((source, index) => (
                  <li key={index}>
                    {source.metadata?.title || source.metadata?.source || "Unknown Source"}
                  </li>
                ))}
              </ul>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}
    </div>
  );
};

export default StreamingMessage;
