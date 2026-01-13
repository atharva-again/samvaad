"use client";

export function Background() {
	return (
		<div className="fixed inset-0 z-0 pointer-events-none">
			<div className="absolute top-[-10%] left-[-5%] w-[40%] h-[40%] bg-signal/10 blur-[120px] rounded-full opacity-50" />
			<div className="absolute bottom-[10%] right-[-5%] w-[35%] h-[35%] bg-purple-600/5 blur-[100px] rounded-full opacity-30" />
			<div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.02] mix-blend-overlay" />
		</div>
	);
}
