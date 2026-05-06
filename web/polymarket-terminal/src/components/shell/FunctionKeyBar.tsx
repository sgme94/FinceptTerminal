import type { PrimaryRoute, TerminalRouteId } from "../../routes/routeConfig";

type FunctionKeyBarProps = {
  activeRouteId: TerminalRouteId;
  routes: PrimaryRoute[];
  onSelectRoute: (routeId: TerminalRouteId) => void;
};

export function FunctionKeyBar({ activeRouteId, routes, onSelectRoute }: FunctionKeyBarProps) {
  return (
    <nav className="function-key-bar" aria-label="Function key routes">
      {routes.map((route) => (
        <button
          className="function-key-button"
          type="button"
          key={route.id}
          aria-current={activeRouteId === route.id ? "page" : undefined}
          onClick={() => onSelectRoute(route.id)}
        >
          <span>{route.functionKey}</span> {route.label}
        </button>
      ))}
    </nav>
  );
}
