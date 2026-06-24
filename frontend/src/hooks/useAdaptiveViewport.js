import { useEffect, useMemo, useState } from "react";

const DEFAULT_STATE = {
  width: 1440,
  height: 900,
  dpr: 1,
  screen: "screen-lg",
  layout: "layout-desktop",
  density: "density-comfort",
  orientation: "orientation-landscape",
  pointer: "pointer-fine",
  tableMode: "table-scroll",
  navMode: "nav-sidebar",
  dashboardCols: 3,
  cssVars: {
    "--adaptive-dashboard-cols": 3,
    "--adaptive-sidebar-width": "clamp(280px, 18.5vw, 318px)",
    "--adaptive-page-padding": "clamp(12px, 1.55vw, 34px)",
    "--adaptive-card-padding": "clamp(14px, 1.2vw, 24px)",
    "--adaptive-panel-gap": "clamp(12px, 1.1vw, 20px)",
    "--adaptive-table-max-height": "min(62vh, 620px)",
  },
};

function readMedia(query) {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia(query).matches;
}

function detectScreen(width) {
  if (width < 560) return "screen-xs";
  if (width < 768) return "screen-sm";
  if (width < 1024) return "screen-md";
  if (width < 1366) return "screen-lg";
  if (width < 1600) return "screen-xl";
  return "screen-xxl";
}

function detectLayout(width, height, pointerCoarse) {
  const portrait = height > width;
  if (width < 768) return "layout-mobile";
  if (width < 1100 || (portrait && width < 1180)) return "layout-tablet";
  if (width < 1450 || pointerCoarse) return "layout-laptop";
  if (width < 1920) return "layout-desktop";
  return "layout-wide";
}

function detectDensity({ width, height, dpr, pointerCoarse }) {
  let pressure = 0;
  if (width < 1280) pressure += 1;
  if (height < 820) pressure += 1;
  if (height < 720) pressure += 1;
  if (dpr >= 1.25 && width < 1600) pressure += 1;
  if (pointerCoarse) pressure += 1;
  if (width >= 1680 && height >= 920 && dpr <= 1.1) pressure -= 1;

  if (pressure >= 2) return "density-compact";
  if (pressure <= -1) return "density-spacious";
  return "density-comfort";
}

function chooseDashboardCols(width, height, density) {
  if (width < 760) return 1;
  if (width < 1180) return 2;
  if (width < 1366 && height < 760) return 2;
  if (density === "density-compact" && width < 1450) return 2;
  return 3;
}

function buildCssVars({ width, height, layout, density, dashboardCols }) {
  const compact = density === "density-compact";
  const spacious = density === "density-spacious";
  const mobile = layout === "layout-mobile";
  const tablet = layout === "layout-tablet";
  const stacked = mobile || tablet;

  return {
    "--adaptive-dashboard-cols": dashboardCols,
    "--adaptive-sidebar-width": stacked
      ? "100%"
      : compact
        ? "clamp(248px, 17vw, 292px)"
        : spacious
          ? "clamp(304px, 18vw, 340px)"
          : "clamp(280px, 18.5vw, 318px)",
    "--adaptive-page-padding": mobile
      ? "12px"
      : compact
        ? "clamp(12px, 1.15vw, 22px)"
        : spacious
          ? "clamp(22px, 1.7vw, 38px)"
          : "clamp(14px, 1.45vw, 32px)",
    "--adaptive-card-padding": mobile
      ? "14px"
      : compact
        ? "clamp(12px, .95vw, 18px)"
        : spacious
          ? "clamp(20px, 1.25vw, 28px)"
          : "clamp(14px, 1.15vw, 24px)",
    "--adaptive-panel-gap": mobile
      ? "12px"
      : compact
        ? "clamp(10px, .9vw, 14px)"
        : spacious
          ? "clamp(18px, 1.2vw, 26px)"
          : "clamp(12px, 1vw, 20px)",
    "--adaptive-title-size": mobile
      ? "clamp(21px, 6vw, 28px)"
      : compact
        ? "clamp(22px, 1.75vw, 30px)"
        : "clamp(24px, 2vw, 36px)",
    "--adaptive-h2-size": compact
      ? "clamp(16px, 1.08vw, 20px)"
      : "clamp(17px, 1.25vw, 23px)",
    "--adaptive-body-size": compact
      ? "clamp(11px, .78vw, 13px)"
      : "clamp(12px, .86vw, 15px)",
    "--adaptive-table-max-height": height < 760
      ? "min(54vh, 460px)"
      : height < 900
        ? "min(58vh, 560px)"
        : "min(64vh, 680px)",
    "--adaptive-content-max-width": width >= 2200 ? "1900px" : "none",
  };
}

function detectViewport() {
  if (typeof window === "undefined") return DEFAULT_STATE;

  const visualViewport = window.visualViewport;
  const width = Math.round(visualViewport?.width || window.innerWidth || DEFAULT_STATE.width);
  const height = Math.round(visualViewport?.height || window.innerHeight || DEFAULT_STATE.height);
  const dpr = Number((window.devicePixelRatio || 1).toFixed(2));
  const pointerCoarse = readMedia("(pointer: coarse)");
  const reducedMotion = readMedia("(prefers-reduced-motion: reduce)");
  const orientation = width >= height ? "orientation-landscape" : "orientation-portrait";
  const screen = detectScreen(width);
  const layout = detectLayout(width, height, pointerCoarse);
  const density = detectDensity({ width, height, dpr, pointerCoarse });
  const dashboardCols = chooseDashboardCols(width, height, density);
  const tableMode = width < 720 ? "table-mobile-scroll" : width < 1280 ? "table-dense-scroll" : "table-wide-scroll";
  const navMode = layout === "layout-mobile" || layout === "layout-tablet" ? "nav-stacked" : "nav-sidebar";

  return {
    width,
    height,
    dpr,
    screen,
    layout,
    density,
    orientation,
    pointer: pointerCoarse ? "pointer-coarse" : "pointer-fine",
    motion: reducedMotion ? "motion-reduce" : "motion-ok",
    tableMode,
    navMode,
    dashboardCols,
    cssVars: buildCssVars({ width, height, layout, density, dashboardCols }),
  };
}

export function useAdaptiveViewport() {
  const [viewport, setViewport] = useState(() => detectViewport());

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    let frame = null;
    const update = () => {
      if (frame) window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => setViewport(detectViewport()));
    };

    update();
    window.addEventListener("resize", update, { passive: true });
    window.addEventListener("orientationchange", update, { passive: true });
    window.visualViewport?.addEventListener("resize", update, { passive: true });

    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", update);
      window.removeEventListener("orientationchange", update);
      window.visualViewport?.removeEventListener("resize", update);
    };
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    root.dataset.viewportScreen = viewport.screen.replace("screen-", "");
    root.dataset.viewportDensity = viewport.density.replace("density-", "");
    root.dataset.viewportLayout = viewport.layout.replace("layout-", "");
    Object.entries(viewport.cssVars || {}).forEach(([key, value]) => root.style.setProperty(key, String(value)));
  }, [viewport]);

  const className = useMemo(() => [
    viewport.screen,
    viewport.layout,
    viewport.density,
    viewport.orientation,
    viewport.pointer,
    viewport.motion,
    viewport.tableMode,
    viewport.navMode,
    `dashboard-cols-${viewport.dashboardCols}`,
  ].filter(Boolean).join(" "), [viewport]);

  return { ...viewport, className };
}
