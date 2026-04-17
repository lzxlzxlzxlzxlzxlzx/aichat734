import { Outlet, useLocation } from "react-router-dom";

import { BottomModeNav } from "../../components/navigation/BottomModeNav";
import { ModeHeader } from "../../components/navigation/ModeHeader";

const modeMeta = {
  "/chat": {
    eyebrow: "聊天模式",
    title: "自然对话与角色引用",
    description: "面向日常聊天、角色引用与多会话切换的工作区。",
  },
  "/play": {
    eyebrow: "游玩模式",
    title: "角色卡驱动的沉浸会话",
    description: "从角色卡进入会话，围绕剧情推进、回溯和状态变化展开。",
  },
  "/creation": {
    eyebrow: "创作模式",
    title: "角色卡与项目资产工作台",
    description: "用于维护角色卡、创作会话与后续世界书资产。",
  },
  "/settings": {
    eyebrow: "系统设置",
    title: "模型、预设与偏好配置",
    description: "承接模型路由、预设管理与全局体验配置。",
  },
} as const;

function getModeCopy(pathname: string) {
  if (pathname.startsWith("/chat")) {
    return modeMeta["/chat"];
  }

  if (pathname.startsWith("/creation")) {
    return modeMeta["/creation"];
  }

  if (pathname.startsWith("/settings")) {
    return modeMeta["/settings"];
  }

  return modeMeta["/play"];
}

function isWorkspaceRoute(pathname: string) {
  return (
    pathname.startsWith("/chat/") ||
    pathname.startsWith("/play/session/") ||
    pathname === "/chat"
  );
}

export function AppShell() {
  const location = useLocation();
  const copy = getModeCopy(location.pathname);
  const workspace = isWorkspaceRoute(location.pathname);

  return (
    <div className={workspace ? "app-shell app-shell--workspace" : "app-shell"}>
      <div className="app-shell__background" aria-hidden="true" />
      <div
        className={
          workspace ? "app-shell__content app-shell__content--workspace" : "app-shell__content"
        }
      >
        {!workspace ? (
          <ModeHeader
            eyebrow={copy.eyebrow}
            title={copy.title}
            description={copy.description}
          />
        ) : null}
        <main className="app-shell__main">
          <Outlet />
        </main>
      </div>
      <BottomModeNav />
    </div>
  );
}
