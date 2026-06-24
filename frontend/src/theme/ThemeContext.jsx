import React, { createContext, useContext, useEffect, useMemo } from "react";
import { asObject } from "../utils.js";

const DEFAULT_THEME_VARS = {
  "--accent": "#2563eb",
  "--accent-2": "#38bdf8",
  "--accent-soft": "#dbeafe",
  "--accent-strong": "#1d4ed8",
  "--sidebar-bg": "#0d2b68",
  "--sidebar-bg-2": "#061a3d",
  "--sidebar-text": "#ffffff",
  "--sidebar-muted": "#b7c9ea",
  "--workspace-bg": "#eef6ff",
  "--card-bg": "#ffffff",
  "--card-bg-soft": "#f8fbff",
  "--text-primary": "#142037",
  "--text-secondary": "#526985",
  "--border": "#d7e3f1",
  "--hero-from": "#0d2b68",
  "--hero-to": "#2563eb",
  "--success": "#16a34a",
  "--warning": "#d97706",
  "--danger": "#dc2626",
  "--surface-glass": "rgba(255,255,255,.72)",
  "--surface-glass-strong": "rgba(255,255,255,.9)",
  "--card-shadow": "0 22px 56px rgba(15, 23, 42, .10)",
  "--shadow-color": "rgba(15, 23, 42, .16)",
  "--nav-hover": "rgba(255,255,255,.10)",
  "--nav-active": "rgba(255,255,255,.18)",
  "--badge-bg": "rgba(37,99,235,.12)",
  "--badge-text": "#1d4ed8",
};

function packageCssVariables(appearancePackage = {}, roleAccent = {}) {
  const pkg = asObject(appearancePackage);
  const cssVars = asObject(pkg.css_variables);
  const accent = cssVars["--accent"] || pkg.accent || roleAccent.accent || DEFAULT_THEME_VARS["--accent"];
  const sidebar = cssVars["--sidebar-bg"] || pkg.sidebar_bg || pkg.sidebar || roleAccent.sidebar || DEFAULT_THEME_VARS["--sidebar-bg"];
  const mode = String(pkg.mode || "light");
  return {
    ...DEFAULT_THEME_VARS,
    ...cssVars,
    "--role-accent": roleAccent.accent || accent,
    "--role-sidebar": roleAccent.sidebar || sidebar,
    "--accent": accent,
    "--sidebar-bg": sidebar,
    "--tenant-accent": accent,
    "--tenant-sidebar": sidebar,
    "--surface-glass": mode === "dark" ? "color-mix(in srgb, var(--card-bg) 74%, transparent)" : "rgba(255,255,255,.72)",
    "--surface-glass-strong": mode === "dark" ? "color-mix(in srgb, var(--card-bg) 92%, transparent)" : "rgba(255,255,255,.9)",
    "--card-shadow": mode === "dark" ? "0 24px 64px rgba(2, 6, 23, .45)" : "0 22px 56px rgba(15, 23, 42, .10)",
    "--shadow-color": mode === "dark" ? "rgba(2, 6, 23, .48)" : "rgba(15, 23, 42, .16)",
    "--nav-hover": mode === "dark" ? "rgba(255,255,255,.08)" : "rgba(255,255,255,.10)",
    "--nav-active": mode === "dark" ? "rgba(255,255,255,.16)" : "rgba(255,255,255,.18)",
    "--badge-bg": `color-mix(in srgb, ${accent} 16%, transparent)`,
    "--badge-text": accent,
  };
}

const ThemeContext = createContext({
  vars: DEFAULT_THEME_VARS,
  packageId: "corporate_blue",
  packageName: "Kurumsal Mavi",
  mode: "light",
  density: "comfort",
});

export function useTenantTheme(appearancePackage = {}, roleAccent = {}, viewportVars = {}) {
  const pkg = asObject(appearancePackage);
  const vars = useMemo(() => ({
    ...viewportVars,
    ...packageCssVariables(pkg, roleAccent),
  }), [pkg, roleAccent?.accent, roleAccent?.sidebar, viewportVars]);

  useEffect(() => {
    const root = document.documentElement;
    Object.entries(vars).forEach(([key, value]) => {
      if (key.startsWith("--")) root.style.setProperty(key, String(value));
    });
  }, [vars]);

  return {
    vars,
    packageId: String(pkg.id || "corporate_blue"),
    packageName: String(pkg.name || "Kurumsal Mavi"),
    mode: String(pkg.mode || "light"),
    density: String(pkg.density || "comfort"),
  };
}

export function TenantThemeProvider({ value, children }) {
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
