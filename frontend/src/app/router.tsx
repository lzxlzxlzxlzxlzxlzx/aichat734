import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import { AppShell } from "./shell/AppShell";
import { ChatPage } from "../features/chat/pages/ChatPage";
import { CreationCardPage } from "../features/creation/pages/CreationCardPage";
import { CreationHomePage } from "../features/creation/pages/CreationHomePage";
import { CreationProjectPage } from "../features/creation/pages/CreationProjectPage";
import { PlayCardDetailPage } from "../features/play/pages/PlayCardDetailPage";
import { PlayHomePage } from "../features/play/pages/PlayHomePage";
import { PlaySessionPage } from "../features/play/pages/PlaySessionPage";
import { SettingsPage } from "../features/system/pages/SettingsPage";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <Navigate to="/play" replace />,
      },
      {
        path: "chat",
        children: [
          { index: true, element: <ChatPage /> },
          { path: ":sessionId", element: <ChatPage /> },
        ],
      },
      {
        path: "play",
        children: [
          { index: true, element: <PlayHomePage /> },
          { path: ":cardId", element: <PlayCardDetailPage /> },
          { path: "session/:sessionId", element: <PlaySessionPage /> },
        ],
      },
      {
        path: "creation",
        children: [
          { index: true, element: <CreationHomePage /> },
          { path: "card/:cardId", element: <CreationCardPage /> },
          { path: "project/:projectId", element: <CreationProjectPage /> },
        ],
      },
      {
        path: "settings",
        element: <SettingsPage />,
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
