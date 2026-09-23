/* Tiny API client shared by all pages. Token lives in localStorage. */
const Api = (() => {
  const KEY = "gym.token";

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.status = status;
    }
  }

  const getToken = () => localStorage.getItem(KEY);
  const setToken = (t) => localStorage.setItem(KEY, t);
  const clearToken = () => localStorage.removeItem(KEY);

  // FastAPI validation errors come back as a list; turn them into one readable sentence.
  function describe(data, status) {
    if (data && typeof data.detail === "string") return data.detail;
    if (data && Array.isArray(data.detail) && data.detail.length) {
      const first = data.detail[0];
      const field = (first.loc || []).filter((p) => p !== "body").pop();
      const msg = String(first.msg || "Invalid value").replace(/^Value error, /, "");
      return field ? `${field.replace(/_/g, " ")}: ${msg}` : msg;
    }
    return status >= 500 ? "Something went wrong on the server. Try again in a moment." : "Request failed.";
  }

  async function request(path, { method = "GET", body, auth = true } = {}) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (auth && getToken()) headers.Authorization = `Bearer ${getToken()}`;

    let res;
    try {
      res = await fetch(`/api${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch {
      throw new ApiError("Can't reach the server. Check your connection.", 0);
    }

    if (res.status === 401 && auth) {
      clearToken();
      window.location.href = "login.html";
      throw new ApiError("Please log in again.", 401);
    }
    if (res.status === 204) return null;

    let data = null;
    try { data = await res.json(); } catch { /* not JSON */ }
    if (!res.ok) throw new ApiError(describe(data, res.status), res.status);
    return data;
  }

  return {
    ApiError, getToken, setToken, clearToken, request,
    get: (path) => request(path),
    post: (path, body, opts) => request(path, { ...opts, method: "POST", body }),
    del: (path) => request(path, { method: "DELETE" }),
  };
})();

/* Build DOM safely (no innerHTML with user data). h("td", {class: "x"}, "text", childNode) */
function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return node;
}
