import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import React from "react";

interface MessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: { metadata?: { title?: string; source?: string } }[];
}

const Message: React.FC<MessageProps> = ({ role, content, sources }) => {
  const isUser = role === "user";

  return (
    <div className={`flex items-start gap-4 ${isUser ? "justify-end" : ""}`} >
      {!isUser && (
        <Avatar>
          <AvatarFallback>AI</AvatarFallback>
        </Avatar>
      )}
      <div
        className={`flex flex-col gap-2 p-3 rounded-lg max-w-[70%] ${
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        }`}
      >
        <p>{content}</p>
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
      {isUser && (
        <Avatar>
          <AvatarFallback>You</AvatarFallback>
        </Avatar>
      )}
    </div>
  );
};

export default Message;
