"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "./Button";
import { Logo } from "./Logo";
import { SeletorDeTema } from "./SeletorDeTema";

export function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-surface-border bg-surface px-6">
      {/* A marca vive na barra lateral, que some no celular. Aqui ela aparece
          só quando a lateral não está: duas marcas na mesma tela é ruído. */}
      <Logo className="text-fg md:hidden" size={26} />
      <span className="hidden md:block" />

      <div className="flex items-center gap-4">
        <SeletorDeTema />
        {/* O nome é o caminho para a própria conta. É onde a pessoa procura
            — inclusive o operador, que não tem "Acessos" no menu e mesmo
            assim precisa poder trocar a própria senha. */}
        {user && (
          <Link
            href="/dashboard/conta"
            className="rounded-lg px-2 py-1 text-right leading-tight transition-colors hover:bg-surface-muted"
          >
            <p className="text-sm font-medium text-fg">{user.nome}</p>
            <p className="text-xs text-fg-muted">{user.email}</p>
          </Link>
        )}
        <Button variant="secondary" onClick={handleLogout}>
          Sair
        </Button>
      </div>
    </header>
  );
}

export default Navbar;
