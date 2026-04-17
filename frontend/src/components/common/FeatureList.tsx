type FeatureListProps = {
  items: string[];
};

export function FeatureList({ items }: FeatureListProps) {
  return (
    <ul className="feature-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}
