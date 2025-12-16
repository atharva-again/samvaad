import { useState, useEffect } from 'react';

export function usePlatform() {
    const [platform, setPlatform] = useState<{ isMac: boolean; modifier: string }>({
        isMac: false,
        modifier: "Alt",
    });

    useEffect(() => {
        if (typeof window !== 'undefined') {
            // Basic check for Mac OS
            const isMac = navigator.userAgent.includes("Mac");
            setPlatform({
                isMac,
                modifier: isMac ? "Option" : "Alt",
            });
        }
    }, []);

    return platform;
}
