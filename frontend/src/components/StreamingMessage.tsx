import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
        return "Thinking...";
      case "streaming":
        return "Responding...";
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
    <div className="flex items-start gap-4">
      <Avatar>
        <AvatarFallback>AI</AvatarFallback>
      </Avatar>
      <div className="flex flex-col gap-2 p-3 rounded-lg max-w-[70%] bg-muted">
        {/* Status indicator */}
        {status !== "complete" && (
          <div className={`text-xs ${getStatusColor()} flex items-center gap-2`}>
            <div className="flex gap-1">
              <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"></div>
            </div>
            {getStatusText()}
          </div>
        )}

        {/* Message content */}
        <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-3 prose-headings:my-2">
          <div className="animate-fade-in">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content + (showCursor ? "▊" : "")}
            </ReactMarkdown>
          </div>
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && status === "complete" && (
          <Accordion type="single" collapsible className="w-full">
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
    </div>
  );
};

export default StreamingMessage;
