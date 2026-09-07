"use client";

import { useCallback, useRef, useState } from "react";
import type { ToastKind } from "@/components/ui";

export interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

const AUTO_DISMISS_MS = 5000;

/**
 * Transient notices.
 *
 * Replaces a single `msg` string that was styled as a success banner
 * regardless of what happened, so failures were reported in green.
 */
export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId.current++;
      setToasts((current) => [...current, { id, kind, message }]);
      setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
    },
    [dismiss],
  );

  return {
    toasts,
    dismiss,
    success: useCallback((message: string) => push("success", message), [push]),
    error: useCallback((message: string) => push("error", message), [push]),
    info: useCallback((message: string) => push("info", message), [push]),
  };
}
