"use client";

import { useEffect } from "react";
import { IS_STATIC_DEMO } from "@/demo/client";

/**
 * Registers the PWA service worker.
 *
 * Skipped in development, where the worker caches the dev bundle and serves
 * stale chunks after a hot reload, and in the static demo, where the app shell
 * it caches is served under a repository path and a stale cache would keep
 * showing an old deploy.
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || IS_STATIC_DEMO) return;
    if (!("serviceWorker" in navigator)) return;

    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Registration fails on insecure origins and in private windows.
      // The app works without it; only offline support is lost.
    });
  }, []);

  return null;
}
