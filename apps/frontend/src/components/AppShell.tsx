"use client";

import { LogOut, Menu, Moon, Sun, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { DemoBanner } from "@/components/DemoBanner";
import { NotificationBell } from "@/components/NotificationBell";
import { Badge } from "@/components/ui";
import { TABS } from "@/lib/constants";
import { initials } from "@/lib/format";
import type { Notification, Session } from "@/lib/types";

export function AppShell({
  user,
  activeTab,
  onTabChange,
  theme,
  onToggleTheme,
  onLogout,
  notifications,
  unreadCount,
  onMarkRead,
  offline,
  children,
}: {
  user: Session | null;
  activeTab: string;
  onTabChange: (tab: string) => void;
  theme: string;
  onToggleTheme: () => void;
  onLogout: () => void;
  notifications: Notification[];
  unreadCount: number;
  onMarkRead: (id: string) => void;
  /** True when no AI provider is configured, so the local analyzer is in use. */
  offline: boolean;
  children: ReactNode;
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  const selectTab = (tab: string) => {
    onTabChange(tab);
    setMenuOpen(false);
  };

  return (
    <div className="min-h-screen">
      <header className="glass sticky top-0 z-40 border-b border-hair">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4">
          <Logo />

          <nav className="hidden lg:flex" aria-label="Seções">
            <div className="flex gap-0.5 rounded-2xl bg-[var(--bg-input)] p-1">
              {TABS.map(({ id, label, icon: Icon }) => {
                const active = activeTab === id;
                return (
                  <button
                    key={id}
                    onClick={() => selectTab(id)}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-1.5 whitespace-nowrap rounded-xl px-3 py-1.5 text-xs font-medium ${
                      active
                        ? "bg-[var(--accent)] text-[var(--accent-contrast)] shadow-[0_4px_14px_-6px_var(--ring)]"
                        : "text-dim hover:bg-[var(--bg-card-hover)] hover:text-body"
                    }`}
                  >
                    <Icon size={13} strokeWidth={2.2} />
                    {label}
                  </button>
                );
              })}
            </div>
          </nav>

          <div className="flex items-center gap-1.5">
            {offline && (
              <span className="hidden sm:block">
                <Badge tone="warning">Modo offline</Badge>
              </span>
            )}
            <NotificationBell
              notifications={notifications}
              unreadCount={unreadCount}
              onMarkRead={onMarkRead}
            />
            <button
              onClick={onToggleTheme}
              aria-label={theme === "dark" ? "Ativar tema claro" : "Ativar tema escuro"}
              className="rounded-lg p-2 text-dim hover:bg-[var(--bg-card-hover)] hover:text-body"
            >
              {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>

            <div className="hidden items-center gap-2 pl-1 sm:flex">
              <span
                className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-accent-soft text-[11px] font-semibold text-accent"
                title={user?.email}
              >
                {initials(user?.full_name || user?.email || "?")}
              </span>
              <button
                onClick={onLogout}
                className="rounded-lg p-2 text-dim hover:bg-[color-mix(in_srgb,var(--danger)_12%,transparent)] hover:text-[var(--danger)]"
                aria-label="Sair"
              >
                <LogOut size={16} />
              </button>
            </div>

            <button
              onClick={() => setMenuOpen((value) => !value)}
              aria-label={menuOpen ? "Fechar menu" : "Abrir menu"}
              aria-expanded={menuOpen}
              className="rounded-lg p-2 text-dim lg:hidden"
            >
              {menuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <nav className="border-t border-hair bg-elevated px-4 py-3 animate-slide-down lg:hidden" aria-label="Seções">
            <div className="grid grid-cols-2 gap-1.5">
              {TABS.map(({ id, label, icon: Icon }) => {
                const active = activeTab === id;
                return (
                  <button
                    key={id}
                    onClick={() => selectTab(id)}
                    className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium ${
                      active
                        ? "bg-[var(--accent)] text-[var(--accent-contrast)]"
                        : "text-dim hover:bg-[var(--bg-card-hover)]"
                    }`}
                  >
                    <Icon size={15} />
                    {label}
                  </button>
                );
              })}
            </div>
            <button
              onClick={onLogout}
              className="mt-2 flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-dim hover:text-[var(--danger)]"
            >
              <LogOut size={15} /> Sair
            </button>
          </nav>
        )}
      </header>

      <DemoBanner />

      <main className="mx-auto max-w-7xl space-y-5 px-4 py-6">{children}</main>
    </div>
  );
}
