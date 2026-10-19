import axios from "axios";
export const api = axios.create({ baseURL: "/api", timeout: 180000 });
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (
      error.response?.status === 401 &&
      !error.config?.url?.includes("/auth/login")
    ) {
      sessionStorage.removeItem("token");
      window.location.assign("/login");
    }
    return Promise.reject(error);
  },
);
export function errorMessage(error: unknown): string {
  return axios.isAxiosError(error)
    ? error.response?.data?.error?.message || error.message
    : "An unexpected error occurred";
}
export function money(
  amount: string | number | null,
  currency: string | null = "INR",
) {
  if (amount === null) return "—";
  return `${currency || ""} ${Number(amount).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
}
