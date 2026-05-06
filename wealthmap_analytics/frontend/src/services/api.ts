import axios from "axios";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? `http://${window.location.hostname}:8000` : "http://localhost:8000");

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ||
  (typeof window !== "undefined" ? `ws://${window.location.hostname}:8000` : "ws://localhost:8000");

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error?.response?.data?.detail || error?.message || "Erro ao conectar com a API";
    return Promise.reject(new Error(message));
  }
);

export const portfolioService = {
  getPortfolio: () => api.get("/portfolio/"),
  getAssets: () => api.get("/assets/"),
  createAsset: (data: any) => api.post("/assets/", data),
  searchAssets: (q: string) => api.get(`/assets/search/?q=${encodeURIComponent(q)}`),
  createTransaction: (data: any) => api.post("/transactions/", data),
};

export const analyticsService = {
  getRisk: () => api.get("/analytics/risk"),
  getForecast: (ticker: string, days = 15) => api.get(`/analytics/forecast/${encodeURIComponent(ticker)}?days=${days}`),
  getSentiment: (ticker: string) => api.get(`/ai/sentiment/${encodeURIComponent(ticker)}`),
  getMacro: () => api.get("/analytics/macro"),
};

export const aiService = {
  chat: (message: string) => api.post("/ai/chat", { message }),
  status: () => api.get("/ai/status"),
};

export default api;
