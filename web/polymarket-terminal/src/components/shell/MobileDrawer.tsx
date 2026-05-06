import { useState } from "react";
import type { TerminalRoute, TerminalRouteId } from "../../routes/routeConfig";

type MobileDrawerProps = {
  activeRouteId: TerminalRouteId;
  routes: TerminalRoute[];
  onSelectRoute: (routeId: TerminalRouteId) => void;
};

export function MobileDrawer({ activeRouteId, routes, onSelectRoute }: MobileDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);

  function selectRoute(routeId: TerminalRouteId) {
    onSelectRoute(routeId);
    setIsOpen(false);
  }

  return (
    <div className="mobile-drawer">
      <button type="button" className="drawer-trigger" onClick={() => setIsOpen((open) => !open)}>
        Open menu
      </button>
      {isOpen ? (
        <nav className="drawer-panel" aria-label="Mobile route drawer">
          {routes.map((route) => (
            <button
              className="drawer-route"
              type="button"
              key={route.id}
              aria-label={`${route.label} drawer`}
              aria-current={activeRouteId === route.id ? "page" : undefined}
              onClick={() => selectRoute(route.id)}
            >
              {route.label}
            </button>
          ))}
        </nav>
      ) : null}
    </div>
  );
}
