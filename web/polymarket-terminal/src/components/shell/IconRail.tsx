import type { TerminalRoute, TerminalRouteId } from "../../routes/routeConfig";

type IconRailProps = {
  activeRouteId: TerminalRouteId;
  routes: TerminalRoute[];
  onSelectRoute: (routeId: TerminalRouteId) => void;
};

export function IconRail({ activeRouteId, routes, onSelectRoute }: IconRailProps) {
  return (
    <aside className="icon-rail" aria-label="Desktop route rail">
      {routes.map((route) => (
        <button
          className="rail-button"
          type="button"
          key={route.id}
          aria-label={`${route.label} rail`}
          aria-current={activeRouteId === route.id ? "page" : undefined}
          onClick={() => onSelectRoute(route.id)}
          title={route.label}
        >
          {route.label.slice(0, 2).toUpperCase()}
        </button>
      ))}
    </aside>
  );
}
