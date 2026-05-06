type EmptyStatePanelProps = {
  title: string;
  description?: string;
};

export function EmptyStatePanel({ title, description }: EmptyStatePanelProps) {
  return (
    <div className="empty-state-panel" role="status">
      <div className="empty-state-title">{title}</div>
      {description ? <p>{description}</p> : null}
    </div>
  );
}
