"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { redisApi, cacheApi } from "@/lib/api";
import { RedisStats, CacheStats } from "@/types";

export function Dashboard() {
  const [redisStats, setRedisStats] = useState<RedisStats | null>(null);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [redis, cache] = await Promise.all([
          redisApi.getStats(),
          cacheApi.getStats(),
        ]);
        setRedisStats(redis);
        setCacheStats(cache);
      } catch (error) {
        console.error("Error fetching stats:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="text-center py-8 text-foreground">Loading dashboard...</div>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-card-foreground">Active Bans</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-card-foreground">{redisStats?.bans.total || 0}</div>
          <p className="text-xs text-muted-foreground mt-1">
            Rate limit and challenge bans
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-card-foreground">Active Throttles</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-card-foreground">{redisStats?.throttles.total || 0}</div>
          <p className="text-xs text-muted-foreground mt-1">
            Cost-based throttles
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-card-foreground">Cache Size</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-card-foreground">{cacheStats?.cache_size || 0}</div>
          <p className="text-xs text-muted-foreground mt-1">
            Suggested questions cached
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-card-foreground">Cache Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold capitalize text-card-foreground">
            {cacheStats?.cache_type?.replace("_", " ") || "N/A"}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Current cache type
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

