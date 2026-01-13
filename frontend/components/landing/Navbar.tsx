"use client";

interface NavbarProps {
	signInWithGoogle: () => void;
}

export function Navbar({ signInWithGoogle }: NavbarProps) {
	return (
		<nav className="fixed top-0 left-0 right-0 z-[100] border-b border-white/[0.05] bg-void/60 backdrop-blur-xl px-4 sm:px-6">
			<div className="flex items-center justify-between py-3 mx-auto max-w-6xl">
				<div className="flex items-center gap-2.5 group cursor-pointer">
					<span className="text-lg font-bold tracking-tight">Samvaad</span>
				</div>
				<button
					type="button"
					onClick={signInWithGoogle}
					className="px-4 py-1.5 text-sm font-semibold transition-all border rounded-full border-white/10 bg-white/5 hover:bg-white/10 active:scale-95"
				>
					Launch App
				</button>
			</div>
		</nav>
	);
}
