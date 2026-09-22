// Silent JWT Token Auto-Refresh and Fetch Interceptor for Zaslon-QDS

interface DecodedJwt {
  exp?: number;
  sub?: string;
  role?: string;
  [key: string]: any;
}

export function parseJwt(token: string): DecodedJwt | null {
  try {
    const base64Url = token.split('.')[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function isTokenExpiredOrNearExpiry(token: string, skewSeconds = 60): boolean {
  const decoded = parseJwt(token);
  if (!decoded || !decoded.exp) return true;
  const now = Math.floor(Date.now() / 1000);
  return decoded.exp - now <= skewSeconds;
}

let refreshPromise: Promise<string | null> | null = null;

export async function silentRefreshToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const currentToken = localStorage.getItem('zaslon_token');
    const port = window.location.port;
    const portRoleMap: Record<string, string> = {
      '5173': 'ALICE',
      '5174': 'EVE',
      '5175': 'BOB',
    };
    const expectedRole = portRoleMap[port];

    // 1. Try canonical /api/v1/auth/refresh
    if (currentToken) {
      try {
        const res = await window.fetch('/api/v1/auth/refresh', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${currentToken}`,
          },
        });

        if (res.ok) {
          const data = await res.json();
          if (data.access_token) {
            localStorage.setItem('zaslon_token', data.access_token);
            window.dispatchEvent(
              new CustomEvent('zaslon_token_refreshed', {
                detail: { token: data.access_token, user: data.user },
              })
            );
            return data.access_token;
          }
        }
      } catch (err) {
        console.warn('Silent refresh endpoint error, falling back:', err);
      }
    }

    // 2. If refresh endpoint failed and we are on a role-locked port (5173, 5174, 5175),
    // automatically re-establish the authentic portal session for the role
    if (expectedRole) {
      try {
        const res = await window.fetch('/api/v1/auth/portal-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ port: parseInt(port, 10), role: expectedRole }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.access_token) {
            localStorage.setItem('zaslon_token', data.access_token);
            window.dispatchEvent(
              new CustomEvent('zaslon_token_refreshed', {
                detail: { token: data.access_token, user: data.user },
              })
            );
            return data.access_token;
          }
        }
      } catch (err) {
        console.error('Portal session fallback failed:', err);
      }
    }

    return null;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

// Intercept window.fetch to automatically refresh expired/near-expiry tokens and retry on 401
const originalFetch = window.fetch.bind(window);

let isInterceptorInstalled = false;

export function setupAuthInterceptor() {
  if (isInterceptorInstalled) return;
  isInterceptorInstalled = true;

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;

    // Do not intercept auth management endpoints to prevent loops
    const bypassUrls = [
      '/api/v1/auth/refresh',
      '/api/v1/auth/login',
      '/api/v1/auth/register',
      '/api/v1/auth/portal-session',
      '/api/v1/auth/seed-demo-users',
    ];

    if (bypassUrls.some((b) => url.includes(b))) {
      return originalFetch(input, init);
    }

    let token = localStorage.getItem('zaslon_token');

    // If token exists and is near expiry (or expired), refresh it before sending
    if (token && isTokenExpiredOrNearExpiry(token)) {
      const refreshedToken = await silentRefreshToken();
      if (refreshedToken) {
        token = refreshedToken;
      }
    }

    // Build headers with Authorization if token is present
    const headers = new Headers(init?.headers || (input instanceof Request ? input.headers : {}));
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const modifiedInit: RequestInit = {
      ...init,
      headers,
    };

    const response = await originalFetch(input, modifiedInit);

    // If 401 Unauthorized, perform one silent refresh and retry
    if (response.status === 401) {
      const refreshedToken = await silentRefreshToken();
      if (refreshedToken) {
        const retryHeaders = new Headers(modifiedInit.headers);
        retryHeaders.set('Authorization', `Bearer ${refreshedToken}`);
        return originalFetch(input, {
          ...modifiedInit,
          headers: retryHeaders,
        });
      }
    }

    return response;
  };
}

// Auto-install on load
setupAuthInterceptor();
