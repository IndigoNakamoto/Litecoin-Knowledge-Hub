'use client';

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';

const TiptapEditor = ({ onChange, content }: { onChange: (richText: string) => void; content?: string }) => {
  const editor = useEditor({
    extensions: [StarterKit],
    content: content || '',
    editorProps: {
      attributes: {
        class: 'rounded-md border min-h-[150px] border-input bg-background px-3 py-2',
      },
    },
    onUpdate({ editor }) {
      onChange(editor.getHTML());
    },
  });

  return (
    <div>
      <EditorContent editor={editor} />
    </div>
  );
};

export default TiptapEditor;
