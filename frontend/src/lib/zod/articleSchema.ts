import { z } from 'zod';

export const articleSchema = z.object({
  title: z.string().min(3, { message: "Title must be at least 3 characters long." }),
  slug: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, { message: "Slug must be in kebab-case." }),
  author_id: z.string().optional(), // Will be handled by the backend, made optional for frontend validation
  tags: z.array(z.string()).optional(),
  category: z.string().min(1, { message: "Category is required." }),
  summary: z.string().optional(),
  // tiptap_content_json will be handled separately by the editor state
});

export type ArticleFormData = z.infer<typeof articleSchema>;
