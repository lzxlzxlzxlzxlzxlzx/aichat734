type ModeHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
};

export function ModeHeader({ eyebrow, title, description }: ModeHeaderProps) {
  return (
    <header className="mode-header">
      <div className="mode-header__eyebrow">{eyebrow}</div>
      <h1 className="mode-header__title">{title}</h1>
      <p className="mode-header__description">{description}</p>
    </header>
  );
}
