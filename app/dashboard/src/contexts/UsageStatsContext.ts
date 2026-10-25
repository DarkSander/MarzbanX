import { fetch } from "service/http";
import { FilterUsageType } from "./DashboardContext";

export type UsagePoint = { date: string; used_traffic: number };

export type UsageTimeline = {
  username: string;
  period: "hour" | "day";
  usages: UsagePoint[];
};

export type TopUser = { username: string; used_traffic: number };

export type UserDevice = { address: string; since: string };

export type UserDevices = {
  username: string;
  limit: number;
  user_limit: number | null;
  default_limit: number;
  devices: UserDevice[];
  checked_at: string | null;
};

const cleanQuery = (query: FilterUsageType) => {
  const result: Record<string, string> = {};
  for (const key in query) {
    const value = query[key as keyof FilterUsageType];
    if (value) result[key] = value;
  }
  return result;
};

export const fetchUserUsageTimeline = (
  username: string,
  query: FilterUsageType
): Promise<UsageTimeline> =>
  fetch(`/user/${encodeURIComponent(username)}/usage/timeline`, {
    query: cleanQuery(query),
  });

export const fetchTopUsers = (
  query: FilterUsageType,
  limit = 10
): Promise<{ usages: TopUser[] }> =>
  fetch("/users/usage/top", { query: { ...cleanQuery(query), limit } });

export const fetchUserDevices = (username: string): Promise<UserDevices> =>
  fetch(`/user/${encodeURIComponent(username)}/devices`);
