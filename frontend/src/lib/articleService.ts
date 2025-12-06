import { ArticleCreate, ArticleUpdate, ArticleRead, ArticleSearchResult } from '@/types/article';

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000/api/v1';

export const ArticleService = {
  async createArticle(articleData: ArticleCreate): Promise<ArticleRead> {
    const response = await fetch(`${API_BASE_URL}/articles`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Add Authorization header if needed
      },
      body: JSON.stringify(articleData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to create article');
    }
    return response.json();
  },

  async getAllArticles(): Promise<ArticleRead[]> {
    const response = await fetch(`${API_BASE_URL}/articles`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // Add Authorization header if needed
      },
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to fetch articles');
    }
    return response.json();
  },

  async getArticleById(id: string): Promise<ArticleRead> {
    const response = await fetch(`${API_BASE_URL}/articles/${id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // Add Authorization header if needed
      },
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to fetch article');
    }
    return response.json();
  },

  async updateArticle(id: string, articleData: ArticleUpdate): Promise<ArticleRead> {
    const response = await fetch(`${API_BASE_URL}/articles/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        // Add Authorization header if needed
      },
      body: JSON.stringify(articleData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to update article');
    }
    return response.json();
  },

  async deleteArticle(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/articles/${id}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        // Add Authorization header if needed
      },
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to delete article');
    }
  },

  async searchArticles(query: string): Promise<ArticleSearchResult[]> {
    if (!query) {
      return [];
    }
    const response = await fetch(`${API_BASE_URL}/articles/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Add Authorization header if needed
      },
      body: JSON.stringify({ query }),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to search articles');
    }
    return response.json();
  },
};
