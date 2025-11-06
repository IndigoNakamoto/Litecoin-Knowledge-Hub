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
        <div className={`text-sm ${getStatusColor()} flex items-center gap-2 mb-2 mx-auto`}>
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"></div>
          </div>
          {getStatusText()}
        </div>
      )}

      {/* Message content */}
      <div className="prose prose-lg max-w-none dark:prose-invert prose-p:my-6 prose-headings:my-4 text-lg leading-relaxed">
        <div className="animate-fade-in">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <h1 className="text-3xl font-bold mt-6 mb-4 text-foreground border-b border-border pb-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-2xl font-semibold mt-5 mb-3 text-foreground">{children}</h2>,
              h3: ({ children }) => <h3 className="text-xl font-semibold mt-4 mb-2 text-foreground">{children}</h3>,
              h4: ({ children }) => <h4 className="text-lg font-semibold mt-3 mb-2 text-foreground">{children}</h4>,
              h5: ({ children }) => <h5 className="text-base font-semibold mt-2 mb-1 text-foreground">{children}</h5>,
              h6: ({ children }) => <h6 className="text-base font-medium mt-2 mb-1 text-muted-foreground">{children}</h6>,
              p: ({ children }) => <p className="my-4 leading-8 text-lg text-foreground">{children}</p>,
              ul: ({ children }) => <ul className="my-4 ml-6 list-disc space-y-2">{children}</ul>,
              ol: ({ children }) => <ol className="my-4 ml-6 list-decimal space-y-2">{children}</ol>,
              li: ({ children }) => <li className="leading-relaxed">{children}</li>,
              code: ({ className, children, ...props }) => {
                const isInline = !className;
                return isInline ? (
                  <code className="bg-muted px-1.5 py-0.5 rounded text-base font-mono" {...props}>
                    {children}
                  </code>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
              pre: ({ children }) => (
                <pre className="bg-muted border border-border rounded-lg p-4 overflow-x-auto my-4 text-base font-mono leading-relaxed">
                  {children}
                </pre>
              ),
              a: ({ href, children }) => (
                <a href={href} className="text-primary hover:text-primary/80 underline underline-offset-2 transition-colors" target="_blank" rel="noopener noreferrer">
                  {children}
                </a>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-primary/30 pl-4 italic my-4 text-muted-foreground">
                  {children}
                </blockquote>
              ),
              strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              hr: () => <hr className="border-border my-6" />,
              table: ({ children }) => (
                <div className="my-4 overflow-x-auto">
                  <table className="w-full border-collapse">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
              th: ({ children }) => <th className="border border-border px-4 py-2 text-left font-semibold">{children}</th>,
              td: ({ children }) => <td className="border border-border px-4 py-2">{children}</td>,
              tr: ({ children, ...props }) => <tr className="even:bg-muted/50" {...props}>{children}</tr>,
              img: ({ src, alt }) => <img src={src} alt={alt} className="rounded-lg my-4 max-w-full" />,
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
              <AccordionTrigger className="text-base">Sources</AccordionTrigger>
              <AccordionContent>
                <ul className="list-disc pl-5 text-sm">
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
