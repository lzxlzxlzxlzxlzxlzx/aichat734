import { Bot, Compass, PenSquare } from "lucide-react";
import { NavLink } from "react-router-dom";

const items = [
  { to: "/chat", label: "聊天", icon: Bot },
  { to: "/play", label: "游玩", icon: Compass },
  { to: "/creation", label: "创作", icon: PenSquare },
];

export function BottomModeNav() {
  return (
    <nav className="bottom-mode-nav" aria-label="主模式导航">
      {items.map((item) => {
        const Icon = item.icon;

        return (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              isActive
                ? "bottom-mode-nav__item bottom-mode-nav__item--active"
                : "bottom-mode-nav__item"
            }
          >
            <Icon size={18} strokeWidth={1.9} />
            <span>{item.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
