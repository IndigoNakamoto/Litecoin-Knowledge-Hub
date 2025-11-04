import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: { metadata?: { title?: string; source?: string } }[];
}

const Message: React.FC<MessageProps> = ({ role, content, sources }) => {
  const isUser = role === "user";

  if (!isUser) {
    // AI messages take full width
    return (
      <div className="w-full">
        <div className="prose prose-lg max-w-none dark:prose-invert prose-p:my-8 prose-headings:my-2 text-lg">
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
            {content}
          </ReactMarkdown>
        </div>
        {sources && sources.length > 0 && (
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
  }

  // User messages remain in chat bubble format
  return (
    <div className="flex items-start gap-4 justify-end">
      <div className="flex flex-col gap-2 p-5 my-8 rounded-tl-3xl rounded-br-3xl rounded-tr-none rounded-bl-none max-w-[70%] bg-primary text-primary-foreground">
        <div className="prose prose-lg max-w-none dark:prose-invert prose-p:my-8 prose-headings:my-2 text-lg">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <h1 className="text-xl font-semibold mt-4 mb-2 text-primary-foreground">{children}</h1>,
              h2: ({ children }) => <h2 className="text-lg font-semibold mt-3 mb-2 text-primary-foreground">{children}</h2>,
              h3: ({ children }) => <h3 className="text-base font-semibold mt-2 mb-1 text-primary-foreground">{children}</h3>,
              h4: ({ children }) => <h4 className="text-sm font-semibold mt-2 mb-1 text-primary-foreground">{children}</h4>,
              h5: ({ children }) => <h5 className="text-sm font-medium mt-1 mb-1 text-primary-foreground">{children}</h5>,
              h6: ({ children }) => <h6 className="text-sm font-medium mt-1 mb-1 text-primary-foreground">{children}</h6>,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
        {sources && sources.length > 0 && (
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

export default Message;
