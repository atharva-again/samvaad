import { useEffect, useState } from "react";

export function usePlatform() {
	const [platform, setPlatform] = useState<{
		isMac: boolean;
		modifier: string;
		isMobile: boolean;
	}>({
		isMac: false,
		modifier: "Alt",
		isMobile: false,
	});

	useEffect(() => {
		if (typeof window !== "undefined") {
			// Navigator platform is deprecated but still useful for broad checks.
			// Also checking userAgent for clearer signals.
			const userAgent = navigator.userAgent;
			const platformStr = navigator.platform;

			const isMac =
				/Mac|iPod|iPhone|iPad/.test(platformStr) || /Mac/.test(userAgent);
			const checkMobile = () => window.innerWidth < 768;

			setPlatform({
				isMac,
				modifier: isMac ? "Option" : "Alt",
				isMobile: checkMobile(),
			});

			const handleResize = () => {
				setPlatform((prev) => ({ ...prev, isMobile: checkMobile() }));
			};

			window.addEventListener("resize", handleResize);
			return () => window.removeEventListener("resize", handleResize);
		}
	}, []);

	return platform;
}
