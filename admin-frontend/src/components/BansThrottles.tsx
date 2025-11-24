"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { redisApi } from "@/lib/api";
import { AlertCircle, CheckCircle2 } from "lucide-react";

export function BansThrottles() {
  const [loading, setLoading] = useState<"bans" | "throttles" | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [confirmAction, setConfirmAction] = useState<"bans" | "throttles" | null>(null);

  const handleClearBans = async () => {
    setLoading("bans");
    setMessage(null);
    try {
      const result = await redisApi.clearBans();
      setMessage({ type: "success", text: result.message });
      setConfirmAction(null);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "Failed to clear bans",
      });
      setConfirmAction(null);
    } finally {
      setLoading(null);
    }
  };

  const handleClearThrottles = async () => {
    setLoading("throttles");
    setMessage(null);
    try {
      const result = await redisApi.clearThrottles();
      setMessage({ type: "success", text: result.message });
      setConfirmAction(null);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "Failed to clear throttles",
      });
      setConfirmAction(null);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Bans & Throttles Management</CardTitle>
          <CardDescription>
            Clear all bans or throttles from Redis. This action cannot be undone.
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
            <div className="space-y-2">
              <h3 className="font-medium text-card-foreground">Clear All Bans</h3>
              <p className="text-sm text-muted-foreground">
                Removes all rate limit bans, challenge bans, and violation records.
              </p>
              {confirmAction === "bans" ? (
                <div className="flex gap-2">
                  <Button
                    variant="destructive"
                    onClick={handleClearBans}
                    disabled={loading === "bans"}
                  >
                    {loading === "bans" ? "Clearing..." : "Confirm Clear Bans"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setConfirmAction(null)}
                    disabled={loading === "bans"}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <Button
                  variant="destructive"
                  onClick={() => setConfirmAction("bans")}
                  disabled={loading !== null}
                >
                  Clear All Bans
                </Button>
              )}
            </div>

            <div className="space-y-2">
              <h3 className="font-medium text-card-foreground">Clear All Throttles</h3>
              <p className="text-sm text-muted-foreground">
                Removes all cost-based throttles.
              </p>
              {confirmAction === "throttles" ? (
                <div className="flex gap-2">
                  <Button
                    variant="destructive"
                    onClick={handleClearThrottles}
                    disabled={loading === "throttles"}
                  >
                    {loading === "throttles" ? "Clearing..." : "Confirm Clear Throttles"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setConfirmAction(null)}
                    disabled={loading === "throttles"}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <Button
                  variant="destructive"
                  onClick={() => setConfirmAction("throttles")}
                  disabled={loading !== null}
                >
                  Clear All Throttles
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

