import { useQuery } from "react-query";
import { fetch } from "service/http";
import { z } from "zod";
import { create } from "zustand";
import { useDashboard } from "./DashboardContext";

export const CertificateSchema = z.object({
  domain: z.string().min(1),
  inbound_tags: z.array(z.string()).default([]),
  auto_renew: z.boolean().default(true),
  apply_to_panel: z.boolean().default(false),
});

export type CertificateFormType = z.infer<typeof CertificateSchema>;

export type CertificateType = {
  id: number;
  domain: string;
  inbound_tags: string[];
  auto_renew: boolean;
  apply_to_panel: boolean;
  status: "pending" | "issued" | "error";
  last_error: string | null;
  issued_at: string | null;
  expires_at: string | null;
  days_remaining: number | null;
  panel_cert_file: string | null;
  panel_key_file: string | null;
};

export const FetchCertificatesQueryKey = "fetch-certificates-query-key";
export const FetchAcmeSettingsQueryKey = "fetch-acme-settings-query-key";

export const AcmeSettingsSchema = z.object({
  email: z.string().email().or(z.literal("")).nullable().optional(),
  cloudflare_api_token: z.string().optional(),
  directory_url: z.string().or(z.literal("")).nullable().optional(),
});

export type AcmeSettingsFormType = z.infer<typeof AcmeSettingsSchema>;

export type AcmeSettingsType = {
  email: string | null;
  cloudflare_api_token_configured: boolean;
  directory_url: string | null;
};

export type CertificateStore = {
  requestCertificate: (cert: CertificateFormType) => Promise<unknown>;
  fetchCertificates: () => Promise<CertificateType[]>;
  reissueCertificate: (cert: CertificateType) => Promise<unknown>;
  deletingCertificate?: CertificateType | null;
  deleteCertificate: () => Promise<unknown>;
  setDeletingCertificate: (cert: CertificateType | null) => void;
  fetchAcmeSettings: () => Promise<AcmeSettingsType>;
  saveAcmeSettings: (settings: AcmeSettingsFormType) => Promise<unknown>;
};

export const useCertificatesQuery = () => {
  const { isEditingCertificates } = useDashboard();
  return useQuery({
    queryKey: FetchCertificatesQueryKey,
    queryFn: useCertificates.getState().fetchCertificates,
    refetchInterval: isEditingCertificates ? 3000 : undefined,
    refetchOnWindowFocus: false,
  });
};

export const useCertificates = create<CertificateStore>((set, get) => ({
  requestCertificate(body) {
    return fetch("/certificates", { method: "POST", body });
  },
  fetchCertificates() {
    return fetch("/certificates");
  },
  reissueCertificate(cert) {
    return fetch(`/certificates/${cert.id}/reissue`, { method: "POST" });
  },
  setDeletingCertificate(cert) {
    set({ deletingCertificate: cert });
  },
  deleteCertificate: () => {
    return fetch(`/certificates/${get().deletingCertificate?.id}`, {
      method: "DELETE",
    });
  },
  fetchAcmeSettings() {
    return fetch("/certificates/settings");
  },
  saveAcmeSettings(body) {
    return fetch("/certificates/settings", { method: "PUT", body });
  },
}));

export const useAcmeSettingsQuery = () => {
  return useQuery({
    queryKey: FetchAcmeSettingsQueryKey,
    queryFn: useCertificates.getState().fetchAcmeSettings,
    refetchOnWindowFocus: false,
  });
};
