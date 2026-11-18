import {
  Navigate,
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
} from "@tanstack/react-router";
import { RootLayout } from "@/src/root-layout";

const rootRoute = createRootRoute({
  component: RootLayout,
  notFoundComponent: () => <Navigate to="/" replace />,
});

const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: lazyRouteComponent(() => import("./routes/home"), "default"),
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: lazyRouteComponent(() => import("./routes/login"), "default"),
});

const authErrorRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/auth-code-error",
  component: lazyRouteComponent(() => import("./routes/auth-error"), "default"),
});

const chatRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/chat/$id",
  component: lazyRouteComponent(() => import("./routes/chat-route"), "default"),
});

const routeTree = rootRoute.addChildren([homeRoute, loginRoute, authErrorRoute, chatRoute]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
  scrollRestoration: true,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
