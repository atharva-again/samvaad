import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	/* config options here */
	reactCompiler: true,
	// Allow tunnel domains for mobile testing
	allowedDevOrigins: [
		"*.loca.lt", // localtunnel
		"*.trycloudflare.com", // cloudflare tunnel
		"*.ngrok.io", // ngrok
		"*.ngrok-free.app", // ngrok free tier
	],
	images: {
		remotePatterns: [
			{
				protocol: "https",
				hostname: "lh3.googleusercontent.com",
			},
		],
	},
};

export default nextConfig;
