import axios from "axios";

function getUserId(): string | null {
  try {
    const raw = localStorage.getItem("auth-storage");
    if (!raw) return null;
    return JSON.parse(raw)?.state?.userId ?? null;
  } catch {
    return null;
  }
}

const baseURL = (import.meta.env.VITE_AGENTS_API_BASE_URL as string | undefined)?.trim() || "http://localhost:8090/api";

export const agentsApiClient = axios.create({
  baseURL,
  timeout: 30000,
});

agentsApiClient.interceptors.request.use((config) => {
  const userId = getUserId();
  if (userId) {
    config.headers = config.headers ?? {};
    config.headers["X-User-Id"] = userId;
  }
  return config;
});
