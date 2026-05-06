export type PrimaryRouteId =
  | "overview"
  | "markets"
  | "signals"
  | "risk"
  | "news"
  | "data"
  | "agents"
  | "audit";

export type SupportRouteId =
  | "strategy-arena"
  | "watchlist"
  | "dataroom"
  | "plans-credits"
  | "settings"
  | "logout";

export type PrimaryRoute = {
  id: PrimaryRouteId;
  label: string;
  functionKey: `F${1 | 2 | 3 | 4 | 5 | 6 | 7 | 8}`;
};

export type SupportRoute = {
  id: SupportRouteId;
  label: string;
};

export type TerminalRoute = PrimaryRoute | SupportRoute;
export type TerminalRouteId = PrimaryRouteId | SupportRouteId;

export const primaryRoutes: PrimaryRoute[] = [
  { id: "overview", label: "Overview", functionKey: "F1" },
  { id: "markets", label: "Markets", functionKey: "F2" },
  { id: "signals", label: "Signals", functionKey: "F3" },
  { id: "risk", label: "Risk", functionKey: "F4" },
  { id: "news", label: "News", functionKey: "F5" },
  { id: "data", label: "Data", functionKey: "F6" },
  { id: "agents", label: "Agents", functionKey: "F7" },
  { id: "audit", label: "Audit", functionKey: "F8" }
];

export const supportRoutes: SupportRoute[] = [
  { id: "strategy-arena", label: "Strategy Arena" },
  { id: "watchlist", label: "Watchlist" },
  { id: "dataroom", label: "Dataroom" },
  { id: "plans-credits", label: "Plans & Credits" },
  { id: "settings", label: "Settings" },
  { id: "logout", label: "Logout" }
];

export const terminalRoutes: TerminalRoute[] = [...primaryRoutes, ...supportRoutes];
