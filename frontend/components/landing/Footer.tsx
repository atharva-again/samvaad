"use client";

export function Footer() {
	return (
		<footer className="relative z-10 px-6 py-16 border-t border-white/[0.05] mx-auto max-w-6xl">
			<div className="flex flex-col md:flex-row justify-between items-start gap-12 mb-16 text-left antialiased">
				<div className="max-w-xs space-y-4">
					<div className="flex items-center gap-2.5">
						<span className="text-lg font-bold tracking-tight">Samvaad</span>
					</div>
					<p className="text-base text-white/30 leading-relaxed italic text-left">
						"Intelligence is the dialogue between knowledge and curiosity."
					</p>
				</div>
				<div className="grid grid-cols-2 gap-16 text-left">
					<div className="space-y-4 text-left">
						<div className="text-[10px] font-bold uppercase tracking-widest text-white/20 text-left">
							Product
						</div>
						<ul className="space-y-3 text-sm text-white/40 font-medium text-left">
							<li className="hover:text-white cursor-pointer transition-colors text-left">
								Features
							</li>
							<li className="hover:text-white cursor-pointer transition-colors text-left">
								Security
							</li>
						</ul>
					</div>
					<div className="space-y-4 text-left">
						<div className="text-[10px] font-bold uppercase tracking-widest text-white/20 text-left">
							Legal
						</div>
						<ul className="space-y-3 text-sm text-white/40 font-medium text-left">
							<li className="hover:text-white cursor-pointer transition-colors text-left">
								Privacy
							</li>
							<li className="hover:text-white cursor-pointer transition-colors text-left">
								Terms
							</li>
						</ul>
					</div>
				</div>
			</div>
			<div className="flex flex-col md:flex-row justify-between items-center gap-4 pt-8 border-t border-white/[0.05] text-white/20 text-[10px] font-bold tracking-[0.2em] uppercase antialiased">
				<div>© 2026 Samvaad Lab</div>
				<div className="flex gap-6">
					<span className="hover:text-white cursor-pointer transition-colors text-left">
						Twitter
					</span>
					<span className="hover:text-white cursor-pointer transition-colors text-left">
						GitHub
					</span>
				</div>
			</div>
		</footer>
	);
}
