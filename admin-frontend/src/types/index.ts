export interface AbusePreventionSettings {
  global_rate_limit_per_minute?: number;
  global_rate_limit_per_hour?: number;
  enable_global_rate_limit?: boolean;
  challenge_ttl_seconds?: number;
  max_active_challenges_per_identifier?: number;
  enable_challenge_response?: boolean;
  high_cost_threshold_usd?: number;
  high_cost_window_seconds?: number;
  enable_cost_throttling?: boolean;
  cost_throttle_duration_seconds?: number;
  daily_cost_limit_usd?: number;
  challenge_request_rate_limit_seconds?: number;
  daily_spend_limit_usd?: number;
  hourly_spend_limit_usd?: number;
  enable_rate_limit_discord_alerts?: boolean;
  enable_spend_limit_discord_alerts?: boolean;
  enable_cost_throttle_discord_alerts?: boolean;
}

export interface SettingsResponse {
  settings: AbusePreventionSettings;
  sources: Record<string, "redis" | "environment">;
}

export interface RedisStats {
  bans: {
    total: number;
    patterns: string[];
  };
  throttles: {
    total: number;
    patterns: string[];
  };
}

export interface CacheStats {
  cache_size: number;
  cache_type: string;
}

