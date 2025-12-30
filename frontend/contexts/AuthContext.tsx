"use client";

import type { Session, User } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { useConversationStore } from "@/lib/stores/useConversationStore";
import { createClient } from "@/utils/supabase/client";

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

export function AuthProvider({ children }: { children: React.ReactNode }) {
	const [user, setUser] = useState<User | null>(null);
	const [session, setSession] = useState<Session | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [hasSeenWalkthrough, setHasSeenWalkthrough] = useState(false);
	const router = useRouter();
	const supabase = createClient();

	useEffect(() => {
		// Sync userId to store for isolation
		const { setUserId } = useConversationStore.getState();
		setUserId(user?.id ?? null);
	}, [user]);

	useEffect(() => {
		const {
			data: { subscription },
		} = supabase.auth.onAuthStateChange(async (event, session) => {
			setSession(session);
			setUser(session?.user ?? null);

			if (session?.user) {
				// Fetch profile data including has_seen_walkthrough
				try {
					const token = session.access_token;
					const response = await fetch(
						`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/users/me`,
						{
							headers: {
								Authorization: `Bearer ${token}`,
							},
						},
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
			if (event === "SIGNED_OUT") {
				setHasSeenWalkthrough(false);
				router.push("/login");
				router.refresh();
			}
		});

		return () => {
			subscription.unsubscribe();
		};
	}, [router, supabase]);

	const signInWithGoogle = async () => {
		await supabase.auth.signInWithOAuth({
			provider: "google",
			options: {
				redirectTo: `${window.location.origin}/auth/callback`,
			},
		});
	};

	const signOut = async () => {
		await supabase.auth.signOut();
		router.push("/login");
		router.refresh();
	};

	const markWalkthroughSeen = async () => {
		if (!session?.access_token) return;
		try {
			const response = await fetch(
				`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/users/walkthrough`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						Authorization: `Bearer ${session.access_token}`,
					},
					body: JSON.stringify({ has_seen: true }),
				},
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
