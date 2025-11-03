import React from "react";

const MessageLoader: React.FC = () => {
  return (
    <div className="flex items-start gap-4">
      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
        <span className="text-xs">AI</span>
      </div>
      <div className="flex flex-col gap-2 p-3 rounded-lg max-w-[70%] bg-muted">
        <div className="flex items-center gap-1">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageLoader;
