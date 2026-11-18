import { Link } from "@tanstack/react-router";

export default function AuthErrorPage() {
  const searchParams = new URLSearchParams(window.location.search);
  const error = searchParams.get("error");
  const errorCode = searchParams.get("error_code");
  const errorDescription = searchParams.get("error_description");

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-black text-white p-4">
      <div className="max-w-md w-full p-8 bg-zinc-900 rounded-xl border border-zinc-800 space-y-6">
        <h1 className="text-2xl font-bold text-red-500">Authentication Error</h1>

        <div className="space-y-2 text-zinc-300">
          <p>
            <span className="font-semibold text-zinc-500">Error:</span> {error}
          </p>
          <p>
            <span className="font-semibold text-zinc-500">Code:</span> {errorCode}
          </p>
          <p>
            <span className="font-semibold text-zinc-500">Description:</span> {errorDescription}
          </p>
        </div>

        <div className="pt-4">
          <Link
            to="/login"
            className="inline-flex h-9 w-full items-center justify-center rounded-md border border-white/10 bg-surface px-4 py-2 text-sm font-medium text-text-primary shadow-sm transition-colors hover:border-white/20 hover:bg-white/5"
          >
            Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
