"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cacheApi } from "@/lib/api";
import { CacheStats } from "@/types";
import { CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";

export function SuggestedQuestionsCache() {
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"clear" | "refresh" | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchStats = async () => {
    try {
      const stats = await cacheApi.getStats();
      setCacheStats(stats);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "Failed to load cache stats",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const handleClear = async () => {
    setActionLoading("clear");
    setMessage(null);
    try {
      const result = await cacheApi.clear();
      setMessage({ type: "success", text: result.message });
      await fetchStats();
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "Failed to clear cache",
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleRefresh = async () => {
    setActionLoading("refresh");
    setMessage(null);
    try {
      const result = await cacheApi.refresh();
      setMessage({ type: "success", text: result.message });
      // Refresh stats after a delay to allow cache to rebuild
      setTimeout(fetchStats, 5000);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "Failed to refresh cache",
      });
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return <div className="text-center py-8 text-foreground">Loading cache stats...</div>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Suggested Questions Cache</CardTitle>
        <CardDescription>
          Manage the suggested questions cache. Clear to remove all cached entries, or refresh to regenerate.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {message && (
          <div
            className={`flex items-center gap-2 p-3 rounded ${
              message.type === "success"
                ? "bg-green-50 text-green-800"
                : "bg-red-50 text-red-800"
            }`}
          >
            {message.type === "success" ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <span className="text-sm">{message.text}</span>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="font-medium mb-2 text-card-foreground">Cache Statistics</h3>
            <div className="space-y-1 text-sm">
              <div>
                <span className="text-muted-foreground">Cache Size: </span>
                <span className="font-medium text-card-foreground">{cacheStats?.cache_size || 0}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Cache Type: </span>
                <span className="font-medium capitalize text-card-foreground">
                  {cacheStats?.cache_type?.replace("_", " ") || "N/A"}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Button
              variant="destructive"
              onClick={handleClear}
              disabled={actionLoading !== null}
            >
              {actionLoading === "clear" ? "Clearing..." : "Clear Cache"}
            </Button>
            <Button
              variant="outline"
              onClick={handleRefresh}
              disabled={actionLoading !== null}
            >
              {actionLoading === "refresh" ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Refreshing...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Regenerate Cache
                </>
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

