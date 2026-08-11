"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "./Button";

export function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-surface-border bg-white px-6">
      <div className="flex items-center gap-2">
        <span aria-hidden="true" className="text-xl">
          🦅
        </span>
        <span className="text-base font-semibold text-gray-900">L&apos;Aquila AI</span>
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="text-right leading-tight">
            <p className="text-sm font-medium text-gray-900">{user.nome}</p>
            <p className="text-xs text-gray-500">{user.email}</p>
          </div>
        )}
        <Button variant="secondary" onClick={handleLogout}>
          Sair
        </Button>
      </div>
    </header>
  );
}

export default Navbar;
