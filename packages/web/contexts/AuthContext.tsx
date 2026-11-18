"use client";

import { useLocation, useNavigate } from "@tanstack/react-router";
import { createContext, useContext, useEffect, useState } from "react";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { apiRequest } from "@/lib/api";
import { authClient } from "@/lib/auth-client";

type SessionData = NonNullable<ReturnType<typeof authClient.useSession>["data"]>;
type AuthUser = SessionData["user"];
type AuthSession = SessionData["session"];

type AuthContextType = {
  user: AuthUser | null;
  session: AuthSession | null;
  isLoading: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  hasSeenWalkthrough: boolean;
  markWalkthroughSeen: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data, isPending } = authClient.useSession();
  const user = data?.user ?? null;
  const userId = user?.id;
  const session = data?.session ?? null;
  const [walkthroughStatus, setWalkthroughStatus] = useState<{
    userId: string;
    hasSeen: boolean;
  } | null>(null);
  const hasSeenWalkthrough =
    !!user && walkthroughStatus?.userId === user.id && walkthroughStatus.hasSeen;
  const navigate = useNavigate();
  const pathname = useLocation({ select: (location) => location.pathname });

  useEffect(() => {
    useConversationStore.getState().setUserId(userId ?? null);
  }, [userId]);

  useEffect(() => {
    if (!userId) return;

    let active = true;
    apiRequest<{ has_seen_walkthrough: boolean }>("/users/me")
      .then((profile) => {
        if (active) {
          setWalkthroughStatus({ userId, hasSeen: profile.has_seen_walkthrough });
        }
      })
      .catch((error: unknown) => {
        console.error("Failed to fetch user profile", error);
      });

    return () => {
      active = false;
    };
  }, [userId]);

  useEffect(() => {
    if (isPending) return;
    const isPublicRoute =
      pathname === "/" || pathname === "/login" || pathname.startsWith("/auth/");

    if (!user && !isPublicRoute) {
      void navigate({ to: "/login", replace: true });
    } else if (user && pathname === "/login") {
      void navigate({ to: "/", replace: true });
    }
  }, [isPending, pathname, navigate, user]);

  const signInWithGoogle = async () => {
    const result = await authClient.signIn.social({
      provider: "google",
      callbackURL: window.location.origin,
      errorCallbackURL: `${window.location.origin}/auth/auth-code-error`,
    });
    if (result.error) {
      throw new Error(result.error.message ?? "Google sign-in failed");
    }
  };

  const signOut = async () => {
    await authClient.signOut();
    await navigate({ to: "/login" });
  };

  const markWalkthroughSeen = async () => {
    try {
      await apiRequest("/users/walkthrough", {
        method: "POST",
        body: { has_seen: true },
      });
      if (user) setWalkthroughStatus({ userId: user.id, hasSeen: true });
    } catch (error) {
      console.error("Failed to update walkthrough status", error);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        isLoading: isPending,
        signInWithGoogle,
        signOut,
        hasSeenWalkthrough,
        markWalkthroughSeen,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
