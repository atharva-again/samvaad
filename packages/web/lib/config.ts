const developmentOrigin =
  typeof window === "undefined" ? "http://localhost:5177" : window.location.origin;

export const API_BASE_URL = import.meta.env.DEV
  ? developmentOrigin
  : import.meta.env.VITE_API_URL || "http://localhost:18765";
