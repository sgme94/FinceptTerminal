import { useEffect, useMemo, useState } from "react";
import {
  primaryRoutes,
  terminalRoutes,
  type PrimaryRoute,
  type TerminalRoute,
  type TerminalRouteId
} from "../../routes/routeConfig";
import { BottomStatusBar } from "./BottomStatusBar";
import { FunctionKeyBar } from "./FunctionKeyBar";
import { IconRail } from "./IconRail";
import { MarketTickerTape } from "./MarketTickerTape";
import { MobileDrawer } from "./MobileDrawer";
import { RightRail } from "./RightRail";

function findRoute(routes: TerminalRoute[], routeId: TerminalRouteId) {
  return routes.find((route) => route.id === routeId) ?? routes[0];
}

function findPrimaryRouteByKey(routes: PrimaryRoute[], key: string) {
  return routes.find((route) => route.functionKey === key);
}

export function TerminalShell() {
  const [activeRouteId, setActiveRouteId] = useState<TerminalRouteId>("overview");
  const activeRoute = useMemo(
    () => findRoute(terminalRoutes, activeRouteId),
    [activeRouteId]
  );

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const route = findPrimaryRouteByKey(primaryRoutes, event.key);

      if (route) {
        event.preventDefault();
        setActiveRouteId(route.id);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="terminal-shell" aria-label="Polymarket terminal">
      <header className="terminal-top">
        <div className="terminal-brand">POLYMARKET TERMINAL</div>
        <FunctionKeyBar
          activeRouteId={activeRouteId}
          routes={primaryRoutes}
          onSelectRoute={setActiveRouteId}
        />
        <MobileDrawer
          activeRouteId={activeRouteId}
          routes={terminalRoutes}
          onSelectRoute={setActiveRouteId}
        />
      </header>
      <MarketTickerTape />
      <div className="terminal-layout">
        <IconRail
          activeRouteId={activeRouteId}
          routes={terminalRoutes}
          onSelectRoute={setActiveRouteId}
        />
        <main className="workspace" aria-label="Main workspace">
          <section className="workspace-panel">
            <p className="workspace-kicker">Workspace</p>
            <h1>{activeRoute.label}</h1>
            <p>{activeRoute.label} static route placeholder.</p>
          </section>
        </main>
        <RightRail />
      </div>
      <BottomStatusBar />
    </div>
  );
}
