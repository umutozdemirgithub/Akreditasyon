import { useMemo } from "react";

export function useSidebarCollapse(viewport = {}) {
  const width = Number(viewport.width || 1440);
  const navMode = viewport.navMode || "nav-sidebar";
  const isTopNavigation = navMode === "nav-stacked" || width < 1100;
  const isCompactSidebar = !isTopNavigation && width < 1320;

  return useMemo(() => ({
    isTopNavigation,
    isCompactSidebar,
    className: [
      isTopNavigation ? "sidebar-topnav" : "sidebar-side",
      isCompactSidebar ? "sidebar-compact" : "",
    ].filter(Boolean).join(" "),
  }), [isTopNavigation, isCompactSidebar]);
}
