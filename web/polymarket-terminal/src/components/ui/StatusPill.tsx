type StatusPillProps = {
  label: string;
  tone?: "neutral" | "ok" | "warn" | "danger" | "mock";
};

export function StatusPill({ label, tone = "neutral" }: StatusPillProps) {
  return <span className={`status-pill status-pill-${tone}`}>{label}</span>;
}
