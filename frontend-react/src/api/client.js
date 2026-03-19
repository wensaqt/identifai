const BASE_URL = import.meta.env.VITE_API_URL || "/api";

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : detail?.message || `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export async function post(path, { body, formData } = {}) {
  const opts = { method: "POST" };
  if (formData) {
    opts.body = formData;
  } else if (body) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE_URL}${path}`, opts);
  const data = await res.json();
  if (!res.ok) throw new ApiError(res.status, data.detail ?? data);
  return data;
}

export async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  const data = await res.json();
  if (!res.ok) throw new ApiError(res.status, data.detail ?? data);
  return data;
}

export async function del(path) {
  const res = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });
  const data = await res.json();
  if (!res.ok) throw new ApiError(res.status, data.detail ?? data);
  return data;
}
