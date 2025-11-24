"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { settingsApi } from "@/lib/api";
import type { AbusePreventionSettings, SettingsResponse } from "@/types";
import { CheckCircle2, AlertCircle } from "lucide-react";

export function AbusePreventionSettings() {
  const [settings, setSettings] = useState<AbusePreventionSettings>({});
  const [sources, setSources] = useState<Record<string, "redis" | "environment">>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response: SettingsResponse = await settingsApi.getSettings();
        setSettings(response.settings);
        setSources(response.sources);
      } catch (error) {
        setMessage({
          type: "error",
          text: error instanceof Error ? error.message : "Failed to load settings",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      await settingsApi.updateSettings(settings);
      setMessage({ type: "success", text: "Settings updated successfully" });
      // Reload settings to get updated sources
      const response: SettingsResponse = await settingsApi.getSettings();
      setSources(response.sources);
    } catch (error) {
      setMessage({
        type: "error",
        text: error instanceof Error ? error.message : "Failed to update settings",
      });
    } finally {
      setSaving(false);
    }
  };

  const updateSetting = (key: keyof AbusePreventionSettings, value: any) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return <div className="text-center py-8 text-foreground">Loading settings...</div>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Abuse Prevention Settings</CardTitle>
        <CardDescription>
          Configure abuse prevention settings. Changes are stored in Redis and take effect immediately.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {message && (
          <div
            className={`flex items-center gap-2 p-3 rounded mb-4 ${
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

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="global_rate_limit_per_minute">
                Global Rate Limit (per minute)
                {sources.global_rate_limit_per_minute && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.global_rate_limit_per_minute})
                  </span>
                )}
              </Label>
              <Input
                id="global_rate_limit_per_minute"
                type="number"
                value={settings.global_rate_limit_per_minute || ""}
                onChange={(e) =>
                  updateSetting("global_rate_limit_per_minute", parseInt(e.target.value) || undefined)
                }
                min="1"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="global_rate_limit_per_hour">
                Global Rate Limit (per hour)
                {sources.global_rate_limit_per_hour && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.global_rate_limit_per_hour})
                  </span>
                )}
              </Label>
              <Input
                id="global_rate_limit_per_hour"
                type="number"
                value={settings.global_rate_limit_per_hour || ""}
                onChange={(e) =>
                  updateSetting("global_rate_limit_per_hour", parseInt(e.target.value) || undefined)
                }
                min="1"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="challenge_ttl_seconds">
                Challenge TTL (seconds)
                {sources.challenge_ttl_seconds && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.challenge_ttl_seconds})
                  </span>
                )}
              </Label>
              <Input
                id="challenge_ttl_seconds"
                type="number"
                value={settings.challenge_ttl_seconds || ""}
                onChange={(e) =>
                  updateSetting("challenge_ttl_seconds", parseInt(e.target.value) || undefined)
                }
                min="60"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max_active_challenges_per_identifier">
                Max Active Challenges per Identifier
                {sources.max_active_challenges_per_identifier && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.max_active_challenges_per_identifier})
                  </span>
                )}
              </Label>
              <Input
                id="max_active_challenges_per_identifier"
                type="number"
                value={settings.max_active_challenges_per_identifier || ""}
                onChange={(e) =>
                  updateSetting("max_active_challenges_per_identifier", parseInt(e.target.value) || undefined)
                }
                min="1"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="high_cost_threshold_usd">
                High Cost Threshold (USD)
                {sources.high_cost_threshold_usd && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.high_cost_threshold_usd})
                  </span>
                )}
              </Label>
              <Input
                id="high_cost_threshold_usd"
                type="number"
                step="0.01"
                value={settings.high_cost_threshold_usd || ""}
                onChange={(e) =>
                  updateSetting("high_cost_threshold_usd", parseFloat(e.target.value) || undefined)
                }
                min="0.01"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="high_cost_window_seconds">
                High Cost Window (seconds)
                {sources.high_cost_window_seconds && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.high_cost_window_seconds})
                  </span>
                )}
              </Label>
              <Input
                id="high_cost_window_seconds"
                type="number"
                value={settings.high_cost_window_seconds || ""}
                onChange={(e) =>
                  updateSetting("high_cost_window_seconds", parseInt(e.target.value) || undefined)
                }
                min="60"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cost_throttle_duration_seconds">
                Cost Throttle Duration (seconds)
                {sources.cost_throttle_duration_seconds && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.cost_throttle_duration_seconds})
                  </span>
                )}
              </Label>
              <Input
                id="cost_throttle_duration_seconds"
                type="number"
                value={settings.cost_throttle_duration_seconds || ""}
                onChange={(e) =>
                  updateSetting("cost_throttle_duration_seconds", parseInt(e.target.value) || undefined)
                }
                min="1"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="challenge_request_rate_limit_seconds">
                Challenge Request Rate Limit (seconds)
                {sources.challenge_request_rate_limit_seconds && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.challenge_request_rate_limit_seconds})
                  </span>
                )}
              </Label>
              <Input
                id="challenge_request_rate_limit_seconds"
                type="number"
                value={settings.challenge_request_rate_limit_seconds || ""}
                onChange={(e) =>
                  updateSetting("challenge_request_rate_limit_seconds", parseInt(e.target.value) || undefined)
                }
                min="1"
              />
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="enable_global_rate_limit"
                checked={settings.enable_global_rate_limit ?? true}
                onChange={(e) => updateSetting("enable_global_rate_limit", e.target.checked)}
                className="h-4 w-4"
              />
              <Label htmlFor="enable_global_rate_limit">
                Enable Global Rate Limit
                {sources.enable_global_rate_limit && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.enable_global_rate_limit})
                  </span>
                )}
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="enable_challenge_response"
                checked={settings.enable_challenge_response ?? true}
                onChange={(e) => updateSetting("enable_challenge_response", e.target.checked)}
                className="h-4 w-4"
              />
              <Label htmlFor="enable_challenge_response">
                Enable Challenge Response
                {sources.enable_challenge_response && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.enable_challenge_response})
                  </span>
                )}
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="enable_cost_throttling"
                checked={settings.enable_cost_throttling ?? true}
                onChange={(e) => updateSetting("enable_cost_throttling", e.target.checked)}
                className="h-4 w-4"
              />
              <Label htmlFor="enable_cost_throttling">
                Enable Cost Throttling
                {sources.enable_cost_throttling && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({sources.enable_cost_throttling})
                  </span>
                )}
              </Label>
            </div>
          </div>

          <Button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save Settings"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

