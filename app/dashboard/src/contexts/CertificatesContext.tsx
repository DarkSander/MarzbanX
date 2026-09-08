import { useQuery } from "react-query";
import { fetch } from "service/http";
import { z } from "zod";
import { create } from "zustand";
import { useDashboard } from "./DashboardContext";

export const CertificateSchema = z.object({
  domain: z.string().min(1),
  inbound_tags: z.array(z.string()).default([]),
  auto_renew: z.boolean().default(true),
});

export type CertificateFormType = z.infer<typeof CertificateSchema>;

export type CertificateType = {
  id: number;
  domain: string;
  inbound_tags: string[];
  auto_renew: boolean;
  status: "pending" | "issued" | "error";
  last_error: string | null;
  issued_at: string | null;
  expires_at: string | null;
  days_remaining: number | null;
};

export const FetchCertificatesQueryKey = "fetch-certificates-query-key";

export type CertificateStore = {
  requestCertificate: (cert: CertificateFormType) => Promise<unknown>;
  fetchCertificates: () => Promise<CertificateType[]>;
  reissueCertificate: (cert: CertificateType) => Promise<unknown>;
  deletingCertificate?: CertificateType | null;
  deleteCertificate: () => Promise<unknown>;
  setDeletingCertificate: (cert: CertificateType | null) => void;
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
}));
