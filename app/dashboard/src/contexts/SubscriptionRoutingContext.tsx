import { useQuery } from "react-query";
import { fetch } from "service/http";

export type SubscriptionRoutingSource =
  | "roscomvpn_default"
  | "roscomvpn_whitelist"
  | "custom_link"
  | "custom_json";

export const PRESET_SOURCES: SubscriptionRoutingSource[] = [
  "roscomvpn_default",
  "roscomvpn_whitelist",
];

export type HappRoutingProfile = {
  Name?: string;
  DirectSites?: string[];
  DirectIp?: string[];
  ProxySites?: string[];
  ProxyIp?: string[];
  BlockSites?: string[];
  BlockIp?: string[];
  [key: string]: unknown;
};

export type SubscriptionRoutingType = {
  enabled: boolean;
  source: SubscriptionRoutingSource;
  custom_value: string | null;
  happ_only: boolean;
  fetched_at: string | null;
  last_error: string | null;
  link: string | null;
  link_length: number | null;
  max_header_size: number;
  profile: HappRoutingProfile | null;
};

export type SubscriptionRoutingModify = Pick<
  SubscriptionRoutingType,
  "enabled" | "source" | "custom_value" | "happ_only"
>;

export const FetchSubscriptionRoutingQueryKey = "fetch-subscription-routing-query-key";

export const fetchSubscriptionRouting = (): Promise<SubscriptionRoutingType> =>
  fetch("/subscription-routing");

export const saveSubscriptionRouting = (
  body: SubscriptionRoutingModify
): Promise<SubscriptionRoutingType> =>
  fetch("/subscription-routing", { method: "PUT", body });

export const refreshSubscriptionRouting = (): Promise<SubscriptionRoutingType> =>
  fetch("/subscription-routing/refresh", { method: "POST" });

export const useSubscriptionRoutingQuery = (enabled: boolean) =>
  useQuery({
    queryKey: FetchSubscriptionRoutingQueryKey,
    queryFn: fetchSubscriptionRouting,
    enabled,
    refetchOnWindowFocus: false,
  });
