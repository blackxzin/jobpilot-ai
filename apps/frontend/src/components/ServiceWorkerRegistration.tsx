"use client";

import { useEffect } from "react";

/**
 * Registers the PWA service worker.
 *
 * Only in production: in development the worker caches the dev bundle and
 * serves stale chunks after a hot reload, which looks like a broken build.
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Registration fails on insecure origins and in private windows.
      // The app works without it; only offline support is lost.
    });
  }, []);

  return null;
}
