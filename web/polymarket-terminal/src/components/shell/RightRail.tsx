export type RightRailItem = {
  id: string;
  label: string;
  detail?: string;
  tone?: "neutral" | "ok" | "warn" | "danger" | "mock";
};

export type RightRailSection = {
  id: "live-news" | "watchlist" | "most-active" | "risk-alerts";
  title: string;
  items?: RightRailItem[];
  emptyLabel?: string;
  error?: string;
};

const defaultSections: RightRailSection[] = [
  {
    id: "live-news",
    title: "Live News",
    items: [
      { id: "rail-news-fed", label: "Fed speaker queue", detail: "fresh 18m", tone: "warn" },
      { id: "rail-news-btc", label: "BTC strike activity", detail: "fresh 26m", tone: "mock" }
    ],
    emptyLabel: "No live news"
  },
  {
    id: "watchlist",
    title: "Watchlist",
    items: [
      { id: "rail-watch-fed", label: "mkt-fed-2026", detail: "64% yes", tone: "ok" },
      { id: "rail-watch-btc", label: "mkt-btc-100k", detail: "41% yes", tone: "neutral" }
    ],
    emptyLabel: "No watchlist markets"
  },
  {
    id: "most-active",
    title: "Most Active",
    items: [
      { id: "rail-active-macro", label: "Macro rates", detail: "$42k mock vol", tone: "mock" },
      { id: "rail-active-crypto", label: "Crypto EOM", detail: "$31k mock vol", tone: "mock" }
    ],
    emptyLabel: "No active markets"
  },
  {
    id: "risk-alerts",
    title: "Risk Alerts",
    items: [
      { id: "rail-risk-paper", label: "Paper-only mode", detail: "No live orders", tone: "ok" },
      { id: "rail-risk-clob", label: "CLOB disabled", detail: "No private keys", tone: "ok" }
    ],
    emptyLabel: "No risk alerts"
  }
];

type RightRailProps = {
  sections?: RightRailSection[];
};

export function RightRail({ sections = defaultSections }: RightRailProps) {
  return (
    <aside className="right-rail" aria-label="Context rail">
      {sections.map((section) => (
        <section className="right-rail-section" aria-label={section.title} key={section.id}>
          <h2>{section.title}</h2>
          {section.error ? (
            <p className="right-rail-error">{section.error}</p>
          ) : section.items && section.items.length > 0 ? (
            <ul className="right-rail-list">
              {section.items.map((item) => (
                <li key={item.id}>
                  <span className={`right-rail-dot right-rail-dot-${item.tone ?? "neutral"}`} />
                  <div>
                    <strong>{item.label}</strong>
                    {item.detail ? <small>{item.detail}</small> : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p>{section.emptyLabel ?? "No items"}</p>
          )}
        </section>
      ))}
    </aside>
  );
}
