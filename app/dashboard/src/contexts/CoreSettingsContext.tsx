import { fetch } from "service/http";
import { create } from "zustand";

export type VlessEncKeyPair = {
  decryption: string;
  encryption: string;
};

export type VlessEncKeys = {
  x25519?: VlessEncKeyPair;
  mlkem768?: VlessEncKeyPair;
};

export type RealityKeys = {
  private_key: string;
  public_key: string;
  short_ids: string[];
  mldsa65_seed?: string;
  mldsa65_verify?: string;
};

export type WireGuardKeyPair = {
  private_key: string;
  public_key: string;
};

export type SelfSignedCert = {
  certificate: string[];
  key: string[];
};

type CoreSettingsStore = {
  isLoading: boolean;
  isPostLoading: boolean;
  fetchCoreSettings: () => void;
  updateConfig: (json: string) => Promise<void>;
  restartCore: () => Promise<void>;
  generateVlessEncKeys: () => Promise<VlessEncKeys>;
  generateRealityKeys: (count?: number) => Promise<RealityKeys>;
  generateWireGuardKeys: () => Promise<WireGuardKeyPair>;
  generateSelfSignedCert: (domain: string) => Promise<SelfSignedCert>;
  version: string | null;
  started: boolean | null;
  logs_websocket: string | null;
  config: string;
};

export const useCoreSettings = create<CoreSettingsStore>((set) => ({
  isLoading: true,
  isPostLoading: false,
  version: null,
  started: false,
  logs_websocket: null,
  config: "",
  fetchCoreSettings: () => {
    set({ isLoading: true });
    Promise.all([
      fetch("/core").then(({ version, started, logs_websocket }) =>
        set({ version, started, logs_websocket })
      ),
      fetch("/core/config").then((config) => set({ config })),
    ]).finally(() => set({ isLoading: false }));
  },
  updateConfig: (body) => {
    set({ isPostLoading: true });
    return fetch("/core/config", { method: "PUT", body }).finally(() => {
      set({ isPostLoading: false });
    });
  },
  restartCore: () => {
    return fetch("/core/restart", { method: "POST" });
  },
  generateVlessEncKeys: () => {
    return fetch("/core/vlessenc");
  },
  generateRealityKeys: (count = 3) => {
    return fetch("/core/reality", { query: { count } });
  },
  generateWireGuardKeys: () => {
    return fetch("/core/wireguard");
  },
  generateSelfSignedCert: (domain: string) => {
    return fetch("/core/self-signed-cert", { query: { domain } });
  },
}));
