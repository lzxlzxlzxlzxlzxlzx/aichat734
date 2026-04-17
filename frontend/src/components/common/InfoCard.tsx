import { ReactNode } from "react";

type InfoCardProps = {
  title: string;
  eyebrow?: string;
  children: ReactNode;
};

export function InfoCard({ title, eyebrow, children }: InfoCardProps) {
  return (
    <article className="info-card">
      {eyebrow ? <div className="info-card__eyebrow">{eyebrow}</div> : null}
      <h3 className="info-card__title">{title}</h3>
      <div className="info-card__body">{children}</div>
    </article>
  );
}
