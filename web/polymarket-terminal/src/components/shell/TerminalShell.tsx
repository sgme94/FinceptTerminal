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
import { AuditPage } from "../../pages/AuditPage";
import { AgentsPage } from "../../pages/AgentsPage";
import { DataPage } from "../../pages/DataPage";
import { MarketsPage } from "../../pages/MarketsPage";
import { NewsPage } from "../../pages/NewsPage";
import { OverviewPage } from "../../pages/OverviewPage";
import { RiskPage } from "../../pages/RiskPage";
import { SignalsPage } from "../../pages/SignalsPage";
import { SupportPage } from "../../pages/SupportPage";

function findRoute(routes: TerminalRoute[], routeId: TerminalRouteId) {
  return routes.find((route) => route.id === routeId) ?? routes[0];
}

function findPrimaryRouteByKey(routes: PrimaryRoute[], key: string) {
  return routes.find((route) => route.functionKey === key);
}

function renderRoute(activeRoute: TerminalRoute) {
  if (activeRoute.id === "overview") {
    return <OverviewPage />;
  }

  if (activeRoute.id === "audit") {
    return <AuditPage />;
  }

  if (activeRoute.id === "markets") {
    return <MarketsPage />;
  }

  if (activeRoute.id === "signals") {
    return <SignalsPage />;
  }

  if (activeRoute.id === "risk") {
    return <RiskPage />;
  }

  if (activeRoute.id === "news") {
    return <NewsPage />;
  }

  if (activeRoute.id === "data") {
    return <DataPage />;
  }

  if (activeRoute.id === "agents") {
    return <AgentsPage />;
  }

  if (!("functionKey" in activeRoute)) {
    return <SupportPage route={activeRoute} />;
  }

  return <OverviewPage />;
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
          {renderRoute(activeRoute)}
        </main>
        <RightRail />
      </div>
      <BottomStatusBar />
    </div>
  );
}
