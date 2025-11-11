'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { useAuthContext } from '@/contexts/AuthContext';
import Link from 'next/link';

interface UserQuestion {
  id?: string;
  question: string;
  chat_history_length: number;
  endpoint_type: 'chat' | 'stream';
  timestamp: string;
  category?: string | null;
  tags: string[];
  analyzed: boolean;
  analyzed_at?: string | null;
}

interface QuestionsResponse {
  questions: UserQuestion[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface QuestionsStats {
  total_questions: number;
  analyzed: number;
  unanalyzed: number;
  by_endpoint: {
    chat: number;
    stream: number;
  };
  date_range: {
    oldest: string | null;
    newest: string | null;
  };
}

export default function QuestionsPage() {
  const [questions, setQuestions] = useState<UserQuestion[]>([]);
  const [stats, setStats] = useState<QuestionsStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [filterAnalyzed, setFilterAnalyzed] = useState<boolean | null>(null);
  const [filterEndpoint, setFilterEndpoint] = useState<string | null>(null);
  const { token } = useAuthContext();

  const loadQuestions = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (filterAnalyzed !== null) {
        params.append('analyzed', filterAnalyzed.toString());
      }
      if (filterEndpoint) {
        params.append('endpoint_type', filterEndpoint);
      }

      // Build headers - include token if available, but don't require it
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/questions/?${params}`,
        {
          method: 'GET',
          headers,
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error: ${response.status}`);
      }

      const data: QuestionsResponse = await response.json();
      setQuestions(data.questions);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred while loading questions.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      // Build headers - include token if available, but don't require it
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/questions/stats`,
        {
          method: 'GET',
          headers,
        }
      );

      if (response.ok) {
        const data: QuestionsStats = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  useEffect(() => {
    loadQuestions();
    loadStats();
  }, [page, filterAnalyzed, filterEndpoint, token]);

  const handleFilterChange = (newFilterAnalyzed: boolean | null, newFilterEndpoint: string | null) => {
    setFilterAnalyzed(newFilterAnalyzed);
    setFilterEndpoint(newFilterEndpoint);
    setPage(1); // Reset to first page when filter changes
  };

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">User Questions Log</h1>
        <Button asChild variant="outline">
          <Link href="/dashboard">Back to Dashboard</Link>
        </Button>
      </div>

      {/* Statistics Card */}
      {stats && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Questions</p>
                <p className="text-2xl font-bold">{stats.total_questions}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Analyzed</p>
                <p className="text-2xl font-bold text-green-600">{stats.analyzed}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Unanalyzed</p>
                <p className="text-2xl font-bold text-yellow-600">{stats.unanalyzed}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">By Endpoint</p>
                <p className="text-sm">
                  Chat: {stats.by_endpoint.chat} | Stream: {stats.by_endpoint.stream}
                </p>
              </div>
            </div>
            {stats.date_range.oldest && stats.date_range.newest && (
              <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                <p>Date Range: {new Date(stats.date_range.oldest).toLocaleDateString()} - {new Date(stats.date_range.newest).toLocaleDateString()}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={filterAnalyzed === null ? "default" : "outline"}
              onClick={() => handleFilterChange(null, filterEndpoint)}
            >
              All Questions
            </Button>
            <Button
              variant={filterAnalyzed === false ? "default" : "outline"}
              onClick={() => handleFilterChange(false, filterEndpoint)}
            >
              Unanalyzed
            </Button>
            <Button
              variant={filterAnalyzed === true ? "default" : "outline"}
              onClick={() => handleFilterChange(true, filterEndpoint)}
            >
              Analyzed
            </Button>
            <Button
              variant={filterEndpoint === null ? "default" : "outline"}
              onClick={() => handleFilterChange(filterAnalyzed, null)}
            >
              All Endpoints
            </Button>
            <Button
              variant={filterEndpoint === "chat" ? "default" : "outline"}
              onClick={() => handleFilterChange(filterAnalyzed, "chat")}
            >
              Chat Only
            </Button>
            <Button
              variant={filterEndpoint === "stream" ? "default" : "outline"}
              onClick={() => handleFilterChange(filterAnalyzed, "stream")}
            >
              Stream Only
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && <p className="text-red-500 mb-4">Error: {error}</p>}

      {isLoading && <p>Loading questions...</p>}

      {!isLoading && !error && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>
                Questions ({total} total)
              </CardTitle>
              <CardDescription>
                Page {page} of {totalPages}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {questions.length > 0 ? (
                <div className="space-y-4">
                  {questions.map((question) => (
                    <div
                      key={question.id || question.timestamp}
                      className="p-4 border rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <p className="text-lg font-medium">{question.question}</p>
                        <div className="flex gap-2">
                          <span className={`text-xs px-2 py-1 rounded ${
                            question.endpoint_type === 'chat'
                              ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200'
                              : 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200'
                          }`}>
                            {question.endpoint_type}
                          </span>
                          {question.analyzed ? (
                            <span className="text-xs px-2 py-1 rounded bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                              Analyzed
                            </span>
                          ) : (
                            <span className="text-xs px-2 py-1 rounded bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200">
                              Unanalyzed
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                        <p>
                          Asked: {new Date(question.timestamp).toLocaleString()}
                          {' | '}
                          Chat History Length: {question.chat_history_length}
                        </p>
                        {question.category && (
                          <p>
                            Category: <span className="font-medium">{question.category}</span>
                          </p>
                        )}
                        {question.tags && question.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            <span>Tags:</span>
                            {question.tags.map((tag, index) => (
                              <span
                                key={index}
                                className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-2 py-1 rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                        {question.analyzed_at && (
                          <p className="text-xs">
                            Analyzed: {new Date(question.analyzed_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">
                  No questions found.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-4">
              <Button
                variant="outline"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="flex items-center px-4">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

