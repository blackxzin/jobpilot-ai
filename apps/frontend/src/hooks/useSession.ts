"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { createDemoClient, IS_STATIC_DEMO } from "@/demo/client";
import { ApiError, createClient, TOKEN_STORAGE_KEY } from "@/lib/api";
import type { Session } from "@/lib/types";

/** In the static demo every request is answered in the browser. */
function clientFor(token: string) {
  return IS_STATIC_DEMO ? createDemoClient() : createClient(token);
}

interface AuthPayload {
  user_id: string;
  email: string;
  full_name: string;
  token: string;
}

/**
 * Session lifecycle: restore, sign in, register, sign out.
 *
 * Sign-in used to POST to /auth/register first and fall back to /auth/login,
 * which silently created an account on every typo'd email and reported a
 * wrong password as a generic failure. The two flows are now distinct.
 */
export function useSession() {
  const [token, setToken] = useState("");
  const [user, setUser] = useState<Session | null>(null);
  const [restoring, setRestoring] = useState(true);

  const client = useMemo(() => clientFor(token), [token]);

  const store = useCallback((next: AuthPayload | null) => {
    if (next) {
      localStorage.setItem(TOKEN_STORAGE_KEY, next.token);
      setToken(next.token);
      setUser(next);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setToken("");
      setUser(null);
    }
  }, []);

  // Restore an existing session, or adopt the token from an OAuth redirect.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const fromRedirect = params.get("token");
    const stored = fromRedirect ?? localStorage.getItem(TOKEN_STORAGE_KEY);

    if (fromRedirect) {
      // Strip the token from the address bar so it does not end up in
      // browser history, bookmarks or a referrer header.
      window.history.replaceState({}, "", window.location.pathname);
    }

    if (!stored) {
      setRestoring(false);
      return;
    }

    // Validate before trusting it: a stored token may have expired while the
    // tab was closed, and restoring it blindly renders a broken shell.
    clientFor(stored)
      .get<{ id: string; email: string; full_name: string }>("/auth/me")
      .then((profile) => {
        localStorage.setItem(TOKEN_STORAGE_KEY, stored);
        setToken(stored);
        setUser({
          user_id: profile.id,
          email: profile.email,
          full_name: profile.full_name,
          token: stored,
        });
      })
      .catch(() => localStorage.removeItem(TOKEN_STORAGE_KEY))
      .finally(() => setRestoring(false));
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      store(await clientFor("").post<AuthPayload>("/auth/login", { email, password }));
    },
    [store],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      store(
        await clientFor("").post<AuthPayload>("/auth/register", {
          email,
          password,
          full_name: fullName,
        }),
      );
    },
    [store],
  );

  /** Sign in to the shared demo account, when the instance exposes one. */
  const loginAsDemo = useCallback(async () => {
    store(await clientFor("").post<AuthPayload>("/auth/demo"));
  }, [store]);

  const logout = useCallback(async () => {
    try {
      await client.post("/auth/logout");
    } catch {
      // A failed round-trip must not trap the user inside a signed-in shell.
    }
    store(null);
  }, [client, store]);

  /** Sign the user out when the backend reports the session is gone. */
  const handleApiError = useCallback(
    (error: unknown): string => {
      if (error instanceof ApiError) {
        if (error.isUnauthorized) {
          store(null);
          return "Sua sessão expirou. Entre novamente.";
        }
        return error.message;
      }
      return "Algo deu errado. Tente novamente.";
    },
    [store],
  );

  return { token, user, client, restoring, login, register, loginAsDemo, logout, handleApiError };
}
