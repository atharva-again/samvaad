"use client";

import { Suspense } from "react";

export default function AuthErrorPage() {
	return (
		<Suspense fallback={<div>Loading...</div>}>
			<ErrorContent />
		</Suspense>
	);
}

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";

function ErrorContent() {
	const searchParams = useSearchParams();
	const error = searchParams.get("error");
	const errorCode = searchParams.get("error_code");
	const errorDescription = searchParams.get("error_description");

	return (
		<div className="flex flex-col items-center justify-center min-h-screen bg-black text-white p-4">
			<div className="max-w-md w-full p-8 bg-zinc-900 rounded-xl border border-zinc-800 space-y-6">
				<h1 className="text-2xl font-bold text-red-500">
					Authentication Error
				</h1>

				<div className="space-y-2 text-zinc-300">
					<p>
						<span className="font-semibold text-zinc-500">Error:</span> {error}
					</p>
					<p>
						<span className="font-semibold text-zinc-500">Code:</span>{" "}
						{errorCode}
					</p>
					<p>
						<span className="font-semibold text-zinc-500">Description:</span>{" "}
						{errorDescription}
					</p>
				</div>

				<div className="pt-4">
					<Link href="/login">
						<Button className="w-full">Back to Login</Button>
					</Link>
				</div>
			</div>
		</div>
	);
}
