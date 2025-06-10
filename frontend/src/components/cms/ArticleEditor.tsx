'use client';

import { useState } from 'react';
import FrontmatterForm from './FrontmatterForm';
import { ArticleFormData } from '@/lib/zod/articleSchema';
import TiptapEditor from './TiptapEditor';

const ArticleEditor = () => {
  const [content, setContent] = useState('');

  const handleFormSubmit = async (data: ArticleFormData) => {
    const articleData = {
      ...data,
      tiptap_content_json: JSON.parse(content || '{}'), // Assuming Tiptap provides JSON
    };
    
    // Replace with your API endpoint
    const response = await fetch('/api/v1/articles', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(articleData),
    });

    if (response.ok) {
      // Handle success (e.g., redirect to dashboard)
      console.log('Article saved successfully');
    } else {
      // Handle error
      console.error('Failed to save article');
    }
  };

  const handleEditorChange = (richText: string) => {
    // For now, we're getting HTML. We'll need to configure Tiptap to output JSON.
    // This is a placeholder.
    setContent(JSON.stringify({ html: richText }));
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Create New Article</h1>
      <div className="space-y-8">
        <FrontmatterForm onSubmit={handleFormSubmit} />
        <div>
          <h2 className="text-xl font-semibold mb-2">Content</h2>
          <TiptapEditor onChange={handleEditorChange} />
        </div>
      </div>
    </div>
  );
};

export default ArticleEditor;
