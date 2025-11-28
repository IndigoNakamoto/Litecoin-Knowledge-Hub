"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { redisApi, cacheApi, questionLogsApi } from "@/lib/api";
import { RedisStats, CacheStats } from "@/types";

interface AverageTokens {
  total: number;
  input: number;
  output: number;
  count: number;
  averageCost: number;
  averageCostWithCache: number;
  totalCount: number;
}

export function Dashboard() {
  const [redisStats, setRedisStats] = useState<RedisStats | null>(null);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [averageTokens, setAverageTokens] = useState<AverageTokens | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [redis, cache, logs] = await Promise.all([
          redisApi.getStats(),
          cacheApi.getStats(),
          questionLogsApi.getRecentLogs(1000).catch(() => ({ logs: [], count: 0 })),
        ]);
        setRedisStats(redis);
        setCacheStats(cache);
        
        // Calculate average tokens (exclude cache hits since they have 0 tokens)
        const nonCacheLogs = logs.logs.filter((log) => !log.cache_hit);
        
        if (logs.logs.length > 0) {
          // Calculate without cache (for token averages)
          let averageCost = 0;
          let avgInput = 0;
          let avgOutput = 0;
          let totalTokens = 0;
          
          if (nonCacheLogs.length > 0) {
            const totalInput = nonCacheLogs.reduce((sum, log) => sum + log.input_tokens, 0);
            const totalOutput = nonCacheLogs.reduce((sum, log) => sum + log.output_tokens, 0);
            totalTokens = totalInput + totalOutput;
            
            avgInput = totalInput / nonCacheLogs.length;
            avgOutput = totalOutput / nonCacheLogs.length;
            
            // Calculate average cost without cache using formula: ((average token in / 1000000 * .1) + (average token out / 1000000 * .4)) * 1000000
            averageCost = ((avgInput / 1000000 * 0.1) + (avgOutput / 1000000 * 0.4)) * 1000000;
          }
          
          // Calculate with cache (includes all requests, cache hits have 0 tokens)
          const totalInputWithCache = logs.logs.reduce((sum, log) => sum + log.input_tokens, 0);
          const totalOutputWithCache = logs.logs.reduce((sum, log) => sum + log.output_tokens, 0);
          
          const avgInputWithCache = totalInputWithCache / logs.logs.length;
          const avgOutputWithCache = totalOutputWithCache / logs.logs.length;
          
          // Calculate average cost with cache using formula: ((average token in / 1000000 * .1) + (average token out / 1000000 * .4)) * 1000000
          const averageCostWithCache = ((avgInputWithCache / 1000000 * 0.1) + (avgOutputWithCache / 1000000 * 0.4)) * 1000000;
          
          setAverageTokens({
            total: Math.round(totalTokens / (nonCacheLogs.length || 1)),
            input: Math.round(avgInput),
            output: Math.round(avgOutput),
            count: nonCacheLogs.length,
            averageCost: averageCost,
            averageCostWithCache: averageCostWithCache,
            totalCount: logs.logs.length,
          });
        } else {
          setAverageTokens(null);
        }
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
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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
      {averageTokens && (
        <>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-card-foreground">Average Tokens</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-bold text-card-foreground">
                Tokens: {averageTokens.total.toLocaleString()} (in: {averageTokens.input.toLocaleString()}, out: {averageTokens.output.toLocaleString()})
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Based on {averageTokens.count} recent requests
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-card-foreground">Average Cost Per Million</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-card-foreground">
                ${averageTokens.averageCost.toFixed(2)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Without cache ({averageTokens.count} requests)
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-card-foreground">Average Cost Per Million</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-card-foreground">
                ${averageTokens.averageCostWithCache.toFixed(2)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                With cache ({averageTokens.totalCount} requests)
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

