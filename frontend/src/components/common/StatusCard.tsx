type StatusCardProps = {
  title: string;
  description: string;
  tone?: "default" | "danger";
};

export function StatusCard({
  title,
  description,
  tone = "default",
}: StatusCardProps) {
  const className =
    tone === "danger" ? "status-card status-card--danger" : "status-card";

  return (
    <div className={className}>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
