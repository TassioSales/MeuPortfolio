"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "./Button";
import { Logo } from "./Logo";

export function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-surface-border bg-white px-6">
      {/* A marca vive na barra lateral, que some no celular. Aqui ela aparece
          só quando a lateral não está: duas marcas na mesma tela é ruído. */}
      <Logo className="text-ink-900 md:hidden" size={26} />
      <span className="hidden md:block" />

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
