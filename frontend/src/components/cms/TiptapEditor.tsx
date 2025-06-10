'use client';

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import TurndownService from 'turndown';
import { useEffect, useState } from 'react';

const TiptapEditor = ({ onChange, content }: { onChange: (markdown: string) => void; content?: string }) => {
  const [turndownService, setTurndownService] = useState<TurndownService | null>(null);

  useEffect(() => {
    setTurndownService(new TurndownService());
  }, []);

  const editor = useEditor({
    extensions: [StarterKit],
    content: content || '',
    immediatelyRender: false, // Add this line to prevent hydration mismatches
    editorProps: {
      attributes: {
        class: 'rounded-md border min-h-[150px] border-input bg-background px-3 py-2',
      },
    },
    onUpdate({ editor }) {
      if (turndownService) {
        const html = editor.getHTML();
        const markdown = turndownService.turndown(html);
        onChange(markdown);
      }
    },
  });

  return (
    <div>
      <EditorContent editor={editor} />
    </div>
  );
};

export default TiptapEditor;
