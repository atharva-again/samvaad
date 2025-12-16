"use client";

import React from "react";
import { LogOut } from "lucide-react";
import { createClient } from "@/utils/supabase/client";
import { useRouter } from "next/navigation";

export function Header() {
  const router = useRouter();
  const [email, setEmail] = React.useState<string | null>(null);

  React.useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user?.email) {
        setEmail(user.email);
      }
    });
  }, []);

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login"); // Redirect to login page
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 bg-void/80 backdrop-blur-md border-b border-white/5">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-signal animate-pulse" />
        <h1 className="text-lg font-medium tracking-tight text-text-primary">
          Samvaad
        </h1>
      </div>

      <div className="flex items-center gap-4 text-xs font-mono text-text-secondary">
        {email && (
          <span className="text-text-tertiary hidden sm:inline-block">
            {email}
          </span>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 hover:bg-white/10 hover:text-red-400 transition-colors cursor-pointer"
        >
          <LogOut className="w-3 h-3" />
          <span>LOG OUT</span>
        </button>
      </div>
    </header>
  );
}
