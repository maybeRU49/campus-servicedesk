const API_URL = (import.meta.env?.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export function getErrorMessage(data, fallback) {
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail)) {
    return data.detail.map((item) => {
      const field = item.loc?.filter((part) => part !== "body").join(".");
      return field ? `${field}: ${item.msg}` : item.msg;
    }).join("; ");
  }
  return fallback;
}

export async function request(path, { method = "GET", body, token, publicRequest = false } = {}) {
  const activeToken = token || localStorage.getItem("access_token");
  const headers = {};
  if (!publicRequest && activeToken) headers.Authorization = `Bearer ${activeToken}`;
  if (body && !(body instanceof URLSearchParams)) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(API_URL + path, {
      method, headers,
      body: body instanceof URLSearchParams ? body : body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Could not connect to the backend. Check your connection and try again.");
  }
  if (!publicRequest && activeToken !== localStorage.getItem("access_token")) {
    throw new Error("Your session changed. Please sign in again.");
  }
  if (response.status === 401 && !publicRequest) {
    window.dispatchEvent(new Event("session-expired"));
    throw new Error("Your session expired. Please sign in again.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(getErrorMessage(data, `Request failed (${response.status}). Please try again.`));
  return data;
}
