"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { usersApi } from "@/lib/api";

interface UserStats {
  total_unique_users: number;
  today_unique_users: number;
  average_users_per_day: number;
  users_over_time: Array<{ date: string; unique_users: number }>;
  days_tracked: number;
}

export function UserStatistics() {
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await usersApi.getStats(days);
        setStats(data);
      } catch (error) {
        console.error("Error fetching user statistics:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 60000); // Refresh every 60 seconds
    return () => clearInterval(interval);
  }, [days]);

  if (loading && !stats) {
    return <div className="text-center py-8 text-foreground">Loading user statistics...</div>;
  }

  if (!stats) {
    return <div className="text-center py-8 text-foreground">Failed to load user statistics</div>;
  }

  // Calculate max users for chart scaling
  const maxUsers = Math.max(
    ...stats.users_over_time.map((day) => day.unique_users),
    stats.today_unique_users
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>User Statistics</CardTitle>
          <CardDescription>
            Unique users tracked by fingerprint over time
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <div className="text-sm font-medium text-muted-foreground">Total Unique Users</div>
              <div className="text-3xl font-bold text-card-foreground">
                {stats.total_unique_users.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">All-time unique users</p>
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-muted-foreground">Today's Unique Users</div>
              <div className="text-3xl font-bold text-card-foreground">
                {stats.today_unique_users.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">Unique users today</p>
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-muted-foreground">Average Per Day</div>
              <div className="text-3xl font-bold text-card-foreground">
                {stats.average_users_per_day.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">
                Average over last {stats.days_tracked} days
              </p>
            </div>
          </div>

          {/* Time Range Selector */}
          <div className="flex gap-2 items-center">
            <label htmlFor="days" className="text-sm font-medium text-foreground">
              Time Range:
            </label>
            <select
              id="days"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="px-3 py-1 border rounded-md bg-background text-foreground"
            >
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="60">Last 60 days</option>
              <option value="90">Last 90 days</option>
            </select>
          </div>

          {/* Users Over Time Chart */}
          <div className="space-y-2">
            <div className="text-sm font-medium text-foreground">Users Over Time</div>
            <div className="border rounded-lg p-4 bg-muted/50 min-h-[300px]">
              {stats.users_over_time.length === 0 ? (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  No data available
                </div>
              ) : (
                <div className="space-y-1">
                  {stats.users_over_time.map((day, index) => {
                    const percentage = maxUsers > 0 ? (day.unique_users / maxUsers) * 100 : 0;
                    const isToday = day.date === new Date().toISOString().split("T")[0];
                    
                    return (
                      <div key={day.date} className="flex items-center gap-2">
                        <div className="w-24 text-xs text-muted-foreground shrink-0">
                          {new Date(day.date).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                          })}
                        </div>
                        <div className="flex-1 relative">
                          <div
                            className={`h-6 rounded ${
                              isToday
                                ? "bg-primary"
                                : "bg-primary/70"
                            } transition-all`}
                            style={{ width: `${Math.max(percentage, 2)}%` }}
                          />
                          <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs font-medium text-primary-foreground">
                            {day.unique_users}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

