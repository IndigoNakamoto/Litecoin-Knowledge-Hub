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
  messageId?: string;
}

const Message: React.FC<MessageProps> = ({ role, content, sources, messageId }) => {
  const isUser = role === "user";
  const messageRef = React.useRef<HTMLDivElement>(null);

  if (!isUser) {
    // AI messages take full width
    return (
      <div ref={messageRef} id={messageId} className="w-full">
        <div className="prose prose-lg max-w-none prose-p:my-6 prose-headings:my-4 leading-relaxed">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <h1 className="font-space-grotesk text-[39px] font-semibold mt-6 mb-4 text-[#222222] border-b border-border pb-2 leading-tight">{children}</h1>,
              h2: ({ children }) => <h2 className="font-space-grotesk text-[30px] font-semibold mt-5 mb-3 text-[#222222] leading-tight">{children}</h2>,
              h3: ({ children }) => <h3 className="font-space-grotesk text-[20px] font-semibold mt-4 mb-2 text-[#222222] leading-tight">{children}</h3>,
              h4: ({ children }) => <h4 className="font-space-grotesk text-lg font-semibold mt-3 mb-2 text-[#222222]">{children}</h4>,
              h5: ({ children }) => <h5 className="font-space-grotesk text-base font-semibold mt-2 mb-1 text-[#222222]">{children}</h5>,
              h6: ({ children }) => <h6 className="font-space-grotesk text-base font-medium mt-2 mb-1 text-gray-600">{children}</h6>,
              p: ({ children }) => <p className="my-4 leading-relaxed text-[16px] text-gray-800">{children}</p>,
              ul: ({ children }) => <ul className="my-4 ml-6 list-disc space-y-2">{children}</ul>,
              ol: ({ children }) => <ol className="my-4 ml-6 list-decimal space-y-2">{children}</ol>,
              li: ({ children }) => <li className="leading-relaxed text-gray-800">{children}</li>,
              code: ({ className, children, ...props }) => {
                const isInline = !className;
                return isInline ? (
                  <code className="bg-muted px-1.5 py-0.5 rounded text-base font-mono text-gray-800" {...props}>
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
                <a href={href} className="text-blue-500 hover:text-blue-600 underline underline-offset-2 transition-colors" target="_blank" rel="noopener noreferrer">
                  {children}
                </a>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-blue-500/30 pl-4 italic my-4 text-gray-600">
                  {children}
                </blockquote>
              ),
              strong: ({ children }) => <strong className="font-semibold text-gray-800">{children}</strong>,
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
              th: ({ children }) => <th className="border border-border px-4 py-2 text-left font-semibold text-gray-800">{children}</th>,
              td: ({ children }) => <td className="border border-border px-4 py-2 text-gray-800">{children}</td>,
              tr: ({ children, ...props }) => <tr className="even:bg-muted/50" {...props}>{children}</tr>,
              img: ({ src, alt }) => <img src={src} alt={alt} className="rounded-lg my-4 max-w-full" />,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>
    );
  }

  // User messages remain in chat bubble format
  return (
    <div ref={messageRef} id={messageId} className="flex items-start gap-4 justify-end">
      <div className="flex flex-col gap-2 p-5 my-8 rounded-tl-3xl rounded-br-3xl rounded-tr-none rounded-bl-none max-w-[70%] bg-[#222222] text-white">
        <div className="prose prose-lg max-w-none prose-p:my-6 prose-headings:my-4 leading-relaxed">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <h1 className="font-space-grotesk text-[39px] font-semibold mt-6 mb-4 text-white border-b border-white/20 pb-2 leading-tight">{children}</h1>,
              h2: ({ children }) => <h2 className="font-space-grotesk text-[30px] font-semibold mt-5 mb-3 text-white leading-tight">{children}</h2>,
              h3: ({ children }) => <h3 className="font-space-grotesk text-[20px] font-semibold mt-4 mb-2 text-white leading-tight">{children}</h3>,
              h4: ({ children }) => <h4 className="font-space-grotesk text-lg font-semibold mt-3 mb-2 text-white">{children}</h4>,
              h5: ({ children }) => <h5 className="font-space-grotesk text-base font-semibold mt-2 mb-1 text-white">{children}</h5>,
              h6: ({ children }) => <h6 className="font-space-grotesk text-base font-medium mt-2 mb-1 text-white/80">{children}</h6>,
              p: ({ children }) => <p className="my-4 leading-relaxed text-[16px] text-white">{children}</p>,
              ul: ({ children }) => <ul className="my-4 ml-6 list-disc space-y-2">{children}</ul>,
              ol: ({ children }) => <ol className="my-4 ml-6 list-decimal space-y-2">{children}</ol>,
              li: ({ children }) => <li className="leading-relaxed text-white">{children}</li>,
              code: ({ className, children, ...props }) => {
                const isInline = !className;
                return isInline ? (
                  <code className="bg-white/20 px-1.5 py-0.5 rounded text-base font-mono text-white" {...props}>
                    {children}
                  </code>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
              pre: ({ children }) => (
                <pre className="bg-white/10 border border-white/20 rounded-lg p-4 overflow-x-auto my-4 text-base font-mono leading-relaxed">
                  {children}
                </pre>
              ),
              a: ({ href, children }) => (
                <a href={href} className="text-white/90 hover:text-white underline underline-offset-2 transition-colors" target="_blank" rel="noopener noreferrer">
                  {children}
                </a>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-white/30 pl-4 italic my-4 text-white/80">
                  {children}
                </blockquote>
              ),
              strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              hr: () => <hr className="border-white/20 my-6" />,
              table: ({ children }) => (
                <div className="my-4 overflow-x-auto">
                  <table className="w-full border-collapse">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => <thead className="bg-white/10">{children}</thead>,
              th: ({ children }) => <th className="border border-white/20 px-4 py-2 text-left font-semibold text-white">{children}</th>,
              td: ({ children }) => <td className="border border-white/20 px-4 py-2 text-white">{children}</td>,
              tr: ({ children, ...props }) => <tr className="even:bg-white/5" {...props}>{children}</tr>,
              img: ({ src, alt }) => <img src={src} alt={alt} className="rounded-lg my-4 max-w-full" />,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
        {sources && sources.length > 0 && (
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="sources">
              <AccordionTrigger className="text-[14px] text-white">Sources</AccordionTrigger>
              <AccordionContent>
                <ul className="list-disc pl-5 text-sm text-white">
                  {sources.map((source, index) => (
                    <li key={index} className="select-text">
                      <span className="no-underline">{source.metadata?.title || source.metadata?.source || "Unknown Source"}</span>
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
