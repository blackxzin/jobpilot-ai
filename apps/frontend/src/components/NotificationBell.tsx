"use client";

import { Bell, BellOff, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui";
import { formatRelative } from "@/lib/format";
import type { Notification } from "@/lib/types";

export function NotificationBell({
  notifications,
  unreadCount,
  onMarkRead,
}: {
  notifications: Notification[];
  unreadCount: number;
  onMarkRead: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click and on Escape — a dropdown that only closes via
  // its own button strands keyboard users.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((value) => !value)}
        aria-label={`Notificações${unreadCount > 0 ? ` (${unreadCount} não lidas)` : ""}`}
        aria-expanded={open}
        className="relative rounded-lg p-2 text-dim hover:bg-[var(--bg-card-hover)] hover:text-body"
      >
        <Bell size={17} />
        {unreadCount > 0 && (
          <span
            className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-bold text-[var(--accent-contrast)]"
            style={{ background: "var(--danger)", color: "#fff" }}
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="surface absolute right-0 top-12 z-50 max-h-96 w-80 overflow-y-auto animate-slide-down">
          <div className="sticky top-0 flex items-center justify-between border-b border-hair bg-card px-4 py-3">
            <span className="text-xs font-semibold">Notificações</span>
            <button onClick={() => setOpen(false)} aria-label="Fechar" className="text-faint hover:text-body">
              <X size={14} />
            </button>
          </div>

          {notifications.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
              <BellOff size={18} className="text-faint" />
              <p className="text-xs text-faint">Nada por aqui ainda.</p>
            </div>
          ) : (
            <ul>
              {notifications.map((notification) => {
                const unread = notification.status !== "read";
                return (
                  <li key={notification.id}>
                    <button
                      onClick={() => unread && onMarkRead(notification.id)}
                      className="w-full border-b border-hair px-4 py-3 text-left hover:bg-[var(--bg-card-hover)]"
                      style={{
                        borderLeft: `2px solid ${unread ? "var(--accent)" : "transparent"}`,
                      }}
                    >
                      <p className="text-xs font-medium">{notification.title}</p>
                      <p className="mt-0.5 line-clamp-2 text-[11px] text-dim">{notification.message}</p>
                      <div className="mt-1.5 flex items-center gap-2">
                        <Badge tone={unread ? "accent" : "neutral"}>{notification.channel}</Badge>
                        <span className="text-[10px] text-faint">
                          {formatRelative(notification.created_at)}
                        </span>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
