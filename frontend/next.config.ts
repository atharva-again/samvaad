import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	reactCompiler: true,
	allowedDevOrigins: [
		"*.loca.lt",
		"*.trycloudflare.com",
		"*.ngrok.io",
		"*.ngrok-free.app",
	],
	images: {
		remotePatterns: [
			{
				protocol: "https",
				hostname: "lh3.googleusercontent.com",
			},
			{
				protocol: "https",
				hostname: "upload.wikimedia.org",
			},
		],
	},
};

export default nextConfig;
