"use client";

import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { questionLogsApi } from "@/lib/api";

interface QuestionLog {
  id: string;
  request_id: string;
  timestamp: string;
  user_question: string;
  assistant_response_length: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  model: string;
  duration_seconds: number;
  status: string;
  sources_count: number;
  cache_hit: boolean;
  cache_type: string | null;
  endpoint_type: string;
}

type CacheFilter = "all" | "cache" | "non-cache";

export function QuestionLogs() {
  const [logs, setLogs] = useState<QuestionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(100);
  const [error, setError] = useState<string | null>(null);
  const [cacheFilter, setCacheFilter] = useState<CacheFilter>("all");

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await questionLogsApi.getRecentLogs(limit);
        setLogs(data.logs);
      } catch (err) {
        console.error("Error fetching question logs:", err);
        setError(err instanceof Error ? err.message : "Failed to fetch question logs");
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [limit]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "success":
        return "text-green-600 dark:text-green-400";
      case "error":
        return "text-red-600 dark:text-red-400";
      default:
        return "text-muted-foreground";
    }
  };

  // Filter logs based on cache filter
  const filteredLogs = useMemo(() => {
    switch (cacheFilter) {
      case "cache":
        return logs.filter((log) => log.cache_hit);
      case "non-cache":
        return logs.filter((log) => !log.cache_hit);
      default:
        return logs;
    }
  }, [logs, cacheFilter]);

  if (loading && logs.length === 0) {
    return <div className="text-center py-8 text-foreground">Loading question logs...</div>;
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 dark:text-red-400">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Question Logs</CardTitle>
              <CardDescription>
                Recent user questions and their responses
              </CardDescription>
            </div>
            <div className="flex gap-4 items-center flex-wrap">
              <div className="flex gap-2 items-center">
                <span className="text-sm font-medium text-foreground">Filter:</span>
                <div className="flex gap-1 border rounded-md p-1 bg-muted/50">
                  <Button
                    variant={cacheFilter === "all" ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setCacheFilter("all")}
                    className="h-7 px-3 text-xs"
                  >
                    All
                  </Button>
                  <Button
                    variant={cacheFilter === "cache" ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setCacheFilter("cache")}
                    className="h-7 px-3 text-xs"
                  >
                    Cache
                  </Button>
                  <Button
                    variant={cacheFilter === "non-cache" ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setCacheFilter("non-cache")}
                    className="h-7 px-3 text-xs"
                  >
                    Non-Cache
                  </Button>
                </div>
              </div>
              <div className="flex gap-2 items-center">
                <label htmlFor="limit" className="text-sm font-medium text-foreground">
                  Limit:
                </label>
                <select
                  id="limit"
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  className="px-3 py-1 border rounded-md bg-background text-foreground"
                >
                  <option value="50">50</option>
                  <option value="100">100</option>
                  <option value="250">250</option>
                  <option value="500">500</option>
                  <option value="1000">1000</option>
                </select>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredLogs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {logs.length === 0
                ? "No question logs found"
                : `No ${cacheFilter === "cache" ? "cache hit" : cacheFilter === "non-cache" ? "non-cache" : ""} question logs found`}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-sm text-muted-foreground mb-2">
                Showing {filteredLogs.length} of {logs.length} logs
              </div>
              {filteredLogs.map((log) => (
                <div
                  key={log.id}
                  className="border rounded-lg p-4 bg-card hover:bg-muted/50 transition-colors"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-foreground">
                          {formatTimestamp(log.timestamp)}
                        </span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-semibold ${
                            log.status === "success"
                              ? "bg-green-800 text-white dark:bg-green-900/30 dark:text-green-300 border border-green-900"
                              : "bg-red-800 text-white dark:bg-red-900/30 dark:text-red-300 border border-red-900"
                          }`}
                          style={{
                            backgroundColor: log.status === "success" ? "#166534" : "#991b1b",
                            color: "#ffffff",
                          }}
                        >
                          {log.status}
                        </span>
                        {log.cache_hit && (
                          <span 
                            className="text-xs px-2 py-0.5 rounded font-semibold bg-blue-800 text-white dark:bg-blue-900/30 dark:text-blue-300 border border-blue-900"
                            style={{
                              backgroundColor: "#1e40af",
                              color: "#ffffff",
                            }}
                          >
                            Cache Hit
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-foreground font-medium mb-2">
                        {log.user_question}
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs text-muted-foreground">
                    <div>
                      <span className="font-medium">Model:</span> {log.model}
                    </div>
                    <div>
                      <span className="font-medium">Endpoint:</span> {log.endpoint_type}
                    </div>
                    <div>
                      <span className="font-medium">Tokens:</span>{" "}
                      {log.input_tokens + log.output_tokens} (in: {log.input_tokens}, out:{" "}
                      {log.output_tokens})
                    </div>
                    <div>
                      <span className="font-medium">Cost:</span> ${log.cost_usd.toFixed(6)}
                    </div>
                    <div>
                      <span className="font-medium">Duration:</span> {log.duration_seconds.toFixed(2)}s
                    </div>
                    <div>
                      <span className="font-medium">Response Length:</span>{" "}
                      {log.assistant_response_length.toLocaleString()} chars
                    </div>
                    <div>
                      <span className="font-medium">Sources:</span> {log.sources_count}
                    </div>
                    {log.cache_type && (
                      <div>
                        <span className="font-medium">Cache Type:</span> {log.cache_type}
                      </div>
                    )}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    <span className="font-medium">Request ID:</span> {log.request_id}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

