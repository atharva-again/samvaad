"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { LoginBanner } from "@/components/login/LoginBanner";
import { LoginForm } from "@/components/login/LoginForm";

export default function LoginPage() {
	const { user, isLoading } = useAuth();
	const router = useRouter();

	useEffect(() => {
		if (user && !isLoading) {
			router.push("/");
		}
	}, [user, isLoading, router]);

	if (isLoading) return null;

	return (
		<div className="min-h-screen w-full grid grid-cols-1 lg:grid-cols-2">
			<div className="order-2 lg:order-1 h-full">
				<LoginForm />
			</div>
			<div className="order-1 lg:order-2 relative hidden lg:block h-full">
				<LoginBanner />
			</div>
		</div>
	);
}
