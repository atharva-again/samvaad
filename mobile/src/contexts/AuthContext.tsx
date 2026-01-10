import type { Session, User } from "@supabase/supabase-js";
import * as WebBrowser from "expo-web-browser";
import { makeRedirectUri } from "expo-auth-session";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { supabase } from "@/lib/supabase";

WebBrowser.maybeCompleteAuthSession();

type AuthContextType = {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  hasSeenWalkthrough: boolean;
  markWalkthroughSeen: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasSeenWalkthrough, setHasSeenWalkthrough] = useState(false);

  useEffect(() => {
    const { setUserId } = useConversationStore.getState();
    setUserId(user?.id ?? null);
  }, [user]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setIsLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);

      if (session?.user) {
        try {
          const token = session.access_token;
          const response = await fetch(
            `${process.env.EXPO_PUBLIC_API_URL || "http://localhost:8001"}/users/me`,
            {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            }
          );
          if (response.ok) {
            const profile = await response.json();
            setHasSeenWalkthrough(profile.has_seen_walkthrough);
          }
        } catch (error) {
          console.error("Failed to fetch user profile", error);
        }
      }

      setIsLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const signInWithGoogle = async () => {
    const redirectUri = makeRedirectUri({
      scheme: "samvaad",
      path: "auth/callback",
    });

    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: redirectUri,
        skipBrowserRedirect: true,
      },
    });

    if (error) {
      console.error("OAuth error:", error);
      return;
    }

    if (data?.url) {
      const result = await WebBrowser.openAuthSessionAsync(
        data.url,
        redirectUri
      );

      if (result.type === "success" && result.url) {
        const url = new URL(result.url);
        const accessToken = url.searchParams.get("access_token");
        const refreshToken = url.searchParams.get("refresh_token");

        if (accessToken && refreshToken) {
          await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
        }
      }
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setHasSeenWalkthrough(false);
  };

  const markWalkthroughSeen = async () => {
    if (!session?.access_token) return;
    try {
      const response = await fetch(
        `${process.env.EXPO_PUBLIC_API_URL || "http://localhost:8001"}/users/walkthrough`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({ has_seen: true }),
        }
      );
      if (response.ok) {
        setHasSeenWalkthrough(true);
      }
    } catch (error) {
      console.error("Failed to update walkthrough status", error);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        isLoading,
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
