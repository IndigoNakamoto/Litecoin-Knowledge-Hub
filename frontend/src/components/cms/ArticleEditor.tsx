'use client';

import { useState } from 'react';
import FrontmatterForm from './FrontmatterForm';
import { ArticleFormData } from '@/lib/zod/articleSchema';
import TiptapEditor from './TiptapEditor';
import { useAuthContext } from '@/contexts/AuthContext';

const ArticleEditor = () => {
  const [content, setContent] = useState('');
  const { token } = useAuthContext();

  const handleFormSubmit = async (data: ArticleFormData) => {
    console.log('Attempting to save article...');
    console.log('Auth Token:', token);

    if (!token) {
      console.error('Authentication token is missing. Cannot save article.');
      alert('You must be logged in to create an article.');
      return;
    }

    const articleData = {
      ...data,
      content_markdown: content,
    };
    
    console.log('Article Data:', articleData);
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    console.log('Backend URL:', backendUrl);

    try {
      const response = await fetch(`${backendUrl}/api/v1/articles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(articleData),
      });

      if (response.ok) {
        console.log('Article saved successfully');
        alert('Article saved successfully!');
        // Optionally, redirect or clear the form
      } else {
        console.error('Failed to save article');
        alert('Failed to save article.');
      }
    } catch (error) {
      console.error('An error occurred during article save:', error);
      alert('An error occurred. Please try again.');
    }
  };

  const handleEditorChange = (markdown: string) => {
    setContent(markdown);
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
