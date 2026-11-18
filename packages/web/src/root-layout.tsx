import { Outlet } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { WalkthroughController } from "@/components/onboarding/WalkthroughController";
import { ChatToaster } from "@/components/ui/ChatToaster";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";

const LiveKitProvider = lazy(() =>
  import("@/components/providers/LiveKitProvider").then((module) => ({
    default: module.LiveKitProvider,
  })),
);

function ApplicationOutlet() {
  const { user } = useAuth();
  const outlet = <Outlet />;

  if (!user) return outlet;

  return (
    <Suspense fallback={null}>
      <LiveKitProvider>{outlet}</LiveKitProvider>
    </Suspense>
  );
}

export function RootLayout() {
  return (
    <>
      <AuthProvider>
        <ApplicationOutlet />
        <WalkthroughController />
      </AuthProvider>
      <ChatToaster />
    </>
  );
}
