let securityToken: string | null = null;
let bootstrap: Promise<string> | null = null;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function clearSecurity() {
  securityToken = null;
  bootstrap = null;
}

async function csrfToken() {
  if (securityToken) return securityToken;
  if (!bootstrap)
    bootstrap = fetch('/api/auth/csrf', { credentials: 'include', cache: 'no-store' })
      .then(async (res) => {
        if (!res.ok)
          throw new ApiError(
            res.status,
            'Could not establish a secure session. Check backend services.',
          );
        return res.json() as Promise<{ csrf_token: string }>;
      })
      .then((data) => {
        securityToken = data.csrf_token;
        return data.csrf_token;
      })
      .finally(() => {
        bootstrap = null;
      });
  return bootstrap;
}

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== 'GET') headers['X-CSRF-Token'] = await csrfToken();
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const response = await fetch(`/api${path}`, {
    method,
    headers,
    credentials: 'include',
    cache: 'no-store',
    body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response
    .json()
    .catch(() => ({ detail: 'Service unavailable. Check that FastAPI is running.' }));
  if (!response.ok) {
    if (response.status === 403 || response.status === 401) clearSecurity();
    const detail = data.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((e: { loc: string[]; msg: string }) => `${e.loc.slice(1).join(' ')}: ${e.msg}`)
              .join('; ')
          : 'Request failed';
    throw new ApiError(response.status, message);
  }
  if (path.startsWith('/auth/') && method !== 'GET') clearSecurity();
  return data as T;
}

export function params(values: Record<string, string | number | undefined>) {
  return new URLSearchParams(
    Object.entries(values)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)]),
  ).toString();
}

export const date = (value: string) =>
  new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
export const human = (value: string) => {
  if (value === 'pending') return 'In Review';
  return value.replaceAll('_', ' ');
};
