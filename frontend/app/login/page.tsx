"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
	const { signInWithGoogle, user, isLoading } = useAuth();
	const router = useRouter();

	useEffect(() => {
		if (user && !isLoading) {
			router.push("/");
		}
	}, [user, isLoading, router]);

	if (isLoading) return null;

	return (
		<div className="min-h-screen w-full flex items-center justify-center bg-void relative overflow-hidden">
			{/* Dynamic Background Elements */}
			<div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0">
				<div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] bg-signal/20 blur-[120px] rounded-full animate-pulse-slow" />
				<div className="absolute top-[40%] right-[10%] w-[40%] h-[60%] bg-purple-500/10 blur-[100px] rounded-full" />
			</div>

			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.6, ease: "easeOut" }}
				className="relative z-10 w-full max-w-md p-8 bg-surface-elevation-1/50 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl"
			>
				<div className="text-center mb-10">
					<h1 className="text-4xl font-light tracking-tight text-white mb-2">
						Samvaad
					</h1>
					<p className="text-white/60 text-sm font-medium tracking-wide uppercase">
						Conversational Intelligence
					</p>
				</div>

				<div className="space-y-6">
					<button
						type="button"
						onClick={signInWithGoogle}
						className="w-full group relative flex items-center justify-center gap-3 px-6 py-4 bg-white text-black rounded-xl font-medium transition-all hover:bg-gray-100 hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-white/5"
					>
						<svg className="w-5 h-5" viewBox="0 0 24 24">
							<title>Google logo</title>
							<path
								fill="currentColor"
								d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
							/>
							<path
								fill="currentColor"
								d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
							/>
							<path
								fill="currentColor"
								d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
							/>
							<path
								fill="currentColor"
								d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
							/>
						</svg>
						<span className="text-lg">Continue with Google</span>
					</button>

					<div className="text-center">
						<p className="text-xs text-white/30">
							By continuing, you agree to our Terms of Service and Privacy
							Policy.
						</p>
					</div>
				</div>
			</motion.div>
		</div>
	);
}
