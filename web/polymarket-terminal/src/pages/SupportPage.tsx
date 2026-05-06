import type { SupportRoute } from "../routes/routeConfig";
import { TerminalButton } from "../components/ui/TerminalButton";
import { StatusPill } from "../components/ui/StatusPill";

type SupportPageProps = {
  route: SupportRoute;
};

export function SupportPage({ route }: SupportPageProps) {
  return (
    <section className="workspace-panel page-stack">
      <div className="page-header">
        <div>
          <p className="workspace-kicker">Support route</p>
          <h1>{route.label}</h1>
        </div>
        <StatusPill label="Disabled in MVP" tone="warn" />
      </div>

      <div className="page-section">
        <h2>Placeholder</h2>
        <p className="detail-copy">
          This support workspace is a placeholder with disabled behavior for the paper-only MVP.
        </p>
        <div className="table-action-row">
          <TerminalButton disabled aria-label={`${route.label} disabled`}>
            {route.label} disabled
          </TerminalButton>
        </div>
      </div>
    </section>
  );
}
