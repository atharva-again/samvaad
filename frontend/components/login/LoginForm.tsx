"use client";

import { useAuth } from "@/contexts/AuthContext";
import Image from "next/image";
import { motion } from "framer-motion";

export const LoginForm = () => {
	const { signInWithGoogle } = useAuth();

	return (
		<div className="relative w-full min-h-[100dvh] flex flex-col justify-center items-center p-6 sm:p-12 md:p-16 lg:p-20 overflow-hidden">
			<div className="absolute inset-0 z-0">
				<Image
					src="https://upload.wikimedia.org/wikipedia/commons/d/d7/Caf%C3%A9_Singer_1879_Edgar_Degas.jpg"
					alt=""
					fill
					className="object-cover object-center blur-3xl opacity-70 scale-110"
					priority
					unoptimized
				/>
			</div>

			<div className="absolute inset-0 z-10 opacity-50 mix-blend-overlay pointer-events-none">
				<svg className="w-full h-full" aria-hidden="true">
					<filter id="noise-form-bg">
						<feTurbulence
							type="fractalNoise"
							baseFrequency="1.2"
							numOctaves="4"
							stitchTiles="stitch"
						/>
						<feColorMatrix type="saturate" values="0" />
					</filter>
					<rect width="100%" height="100%" filter="url(#noise-form-bg)" />
				</svg>
			</div>

			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 1, ease: "easeOut" }}
				className="relative z-20 text-center max-w-md w-full px-4"
			>
				<h1 className="font-playfair text-5xl sm:text-6xl md:text-8xl text-white tracking-tight leading-none mb-6">
					Samvaad
				</h1>
				<p className="text-base sm:text-lg md:text-xl text-white/40 font-light max-w-md mx-auto leading-relaxed mb-12">
					Intelligence is the dialogue between
					<br />
					<span className="text-white/80 italic font-serif">knowledge</span> and{" "}
					<span className="text-white/80 italic font-serif">curiosity</span>.
				</p>

				{/* Continue with Google Button */}
				<div className="w-full max-w-xs mx-auto mt-8">
					<button
						type="button"
						onClick={signInWithGoogle}
						className="w-full group relative flex items-center justify-center gap-3 px-6 py-4 bg-white text-black rounded-xl font-medium transition-all hover:bg-gray-100 hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-white/5 cursor-pointer"
					>
						<svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
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
						<span className="text-base sm:text-lg whitespace-nowrap">
							Continue with Google
						</span>
					</button>
				</div>
			</motion.div>
		</div>
	);
};
