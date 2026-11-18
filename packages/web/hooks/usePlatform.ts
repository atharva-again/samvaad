import { useEffect, useState } from "react";

export function usePlatform() {
  const [platform, setPlatform] = useState<{
    isMac: boolean;
    modifier: string;
    isMobile: boolean;
  }>(() => {
    if (typeof window === "undefined") {
      return { isMac: false, modifier: "Alt", isMobile: false };
    }
    const userAgent = navigator.userAgent;
    const platformStr = navigator.platform;
    const isMac = /Mac|iPod|iPhone|iPad/.test(platformStr) || /Mac/.test(userAgent);
    return {
      isMac,
      modifier: isMac ? "Option" : "Alt",
      isMobile: window.innerWidth < 768,
    };
  });

  useEffect(() => {
    const handleResize = () => {
      setPlatform((prev) => ({ ...prev, isMobile: window.innerWidth < 768 }));
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return platform;
}
