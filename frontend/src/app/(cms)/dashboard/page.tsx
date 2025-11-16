'use client'; // Required for useState, useEffect, event handlers

import Link from 'next/link';
import { useState, FormEvent, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthContext } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

// Define a type for the articles returned by the search
interface SearchArticle {
  id: string;
  title: string;
  slug: string;
  author_id?: string;
  tags: string[];
  summary?: string;
  vetting_status: string;
  created_at: string; // Assuming ISO string format
  updated_at: string; // Assuming ISO string format
  // Add other fields from ArticleRead if needed for display
}

// Your API returns articles directly as an array
type AllArticlesResponse = SearchArticle[];

export default function DashboardPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [allArticles, setAllArticles] = useState<SearchArticle[]>([]);
  const [displayedArticles, setDisplayedArticles] = useState<SearchArticle[]>([]);
  const [isLoading, setIsLoading] = useState(true); // Start with loading true
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token } = useAuthContext();

  // Load all articles on component mount
  useEffect(() => {
    const loadAllArticles = async () => {
      if (!token) {
        setError("Authentication token not found. Please log in.");
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/articles`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Error: ${response.status}`);
        }

        const data: AllArticlesResponse = await response.json();
        // Your API returns articles directly as an array
        setAllArticles(data);
        setDisplayedArticles(data);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('An unknown error occurred while loading articles.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadAllArticles();
  }, [token]);

  const MAX_QUERY_LENGTH = 1000;

  const handleSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    
    // If search query is empty, show all articles
    const trimmedQuery = searchQuery.trim();
    if (!trimmedQuery) {
      setDisplayedArticles(allArticles);
      return;
    }

    // Validate search query length
    if (trimmedQuery.length > MAX_QUERY_LENGTH) {
      setError(`Search query is too long. Maximum length is ${MAX_QUERY_LENGTH} characters. Your query is ${trimmedQuery.length} characters.`);
      return;
    }

    if (!token) {
      setError("Authentication token not found. Please log in.");
      return;
    }

    setIsSearching(true);
    setError(null);

    try {
      // Build query parameters for GET request
      const params = new URLSearchParams({
        query: trimmedQuery,
        limit: '50' // Changed from top_k to limit to match backend
      });

      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/articles/search/?${params}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error: ${response.status}`);
      }

      const data: SearchArticle[] = await response.json();
      setDisplayedArticles(data || []);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred during search.');
      }
      // On search error, keep showing current articles
    } finally {
      setIsSearching(false);
    }
  };

  // Handle clearing search
  const handleClearSearch = () => {
    setSearchQuery('');
    setDisplayedArticles(allArticles);
  };

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Litecoin Knowledge Hub Dashboard</h1>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href="/questions">View Questions Log</Link>
          </Button>
          <Button asChild size="lg">
            <Link href="/editor/new">Create New Article</Link>
          </Button>
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Search Articles</CardTitle>
          <CardDescription>
            Find articles by keywords or topics. Leave empty to show all articles.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-2">
            <Input
              type="search"
              placeholder="Enter search query..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-grow"
            />
            <Button type="submit" disabled={isSearching}>
              {isSearching ? 'Searching...' : 'Search'}
            </Button>
            {searchQuery && (
              <Button 
                type="button" 
                variant="outline" 
                onClick={handleClearSearch}
                disabled={isSearching}
              >
                Clear
              </Button>
            )}
          </form>
        </CardContent>
      </Card>

      {error && <p className="text-red-500 mb-4">Error: {error}</p>}

      {isLoading && <p>Loading articles...</p>}

      {!isLoading && !error && (
        <Card>
          <CardHeader>
            <CardTitle>
              {searchQuery ? `Search Results (${displayedArticles.length})` : `All Articles (${displayedArticles.length})`}
            </CardTitle>
            {searchQuery && (
              <CardDescription>
                Showing results for:&nbsp;
                <span className="font-medium">&ldquo;{searchQuery}&rdquo;</span>
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {displayedArticles.length > 0 ? (
              <ul className="space-y-3">
                {displayedArticles.map((article) => (
                  <li key={article.id} className="p-3 border rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    <Link href={`/editor/${article.id}`} className="block">
                      <h3 className="text-lg font-semibold text-blue-600 dark:text-blue-400 hover:underline">{article.title}</h3>
                    </Link>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Slug: {article.slug}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Status: 
                      <span className={`font-medium ml-1 ${
                        article.vetting_status === 'vetted' ? 'text-green-600' : 
                        article.vetting_status === 'pending' ? 'text-yellow-600' : 
                        'text-red-600'
                      }`}>
                        {article.vetting_status}
                      </span>
                    </p>
                    {article.summary && (
                      <p className="text-sm text-gray-700 dark:text-gray-300 mt-1 line-clamp-2">
                        {article.summary}
                      </p>
                    )}
                    {article.tags && article.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {article.tags.slice(0, 3).map((tag, index) => (
                          <span key={index} className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
                            {tag}
                          </span>
                        ))}
                        {article.tags.length > 3 && (
                          <span className="text-xs text-gray-500">+{article.tags.length - 3} more</span>
                        )}
                      </div>
                    )}
                    <div className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                      <span>Created: {new Date(article.created_at).toLocaleDateString()}</span>
                      {' | '}
                      <span>Updated: {new Date(article.updated_at).toLocaleDateString()}</span>
                      {' | '}
                      <span>ID: {article.id}</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 text-center py-8">
                {searchQuery ? 'No articles found for your search query.' : 'No articles available.'}
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}