"use client";

import { Suspense, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { useAuth } from "@/hooks/useAuth";
import { DEFAULT_AUTHENTICATED_ROUTE } from "@/lib/constants";

/**
 * Só aceita caminho interno: `?next=https://outro-site` seria um
 * open redirect.
 */
function safeRedirect(next: string | null): string {
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  return DEFAULT_AUTHENTICATED_ROUTE;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, error, clearError } = useAuth();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearError();
    setIsSubmitting(true);

    try {
      await login(email, senha);
      router.replace(safeRedirect(searchParams.get("next")));
    } catch {
      // A mensagem já está no store; mantém o usuário no formulário.
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <span aria-hidden="true" className="text-3xl">
            🦅
          </span>
          <h1 className="mt-2 text-2xl font-semibold text-gray-900">
            Entrar na L&apos;Aquila AI
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Acesse o painel dos seus agentes de WhatsApp.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-xl border border-surface-border bg-white p-6 shadow-sm"
        >
          <Input
            label="E-mail"
            type="email"
            name="email"
            autoComplete="email"
            placeholder="voce@empresa.com"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <Input
            label="Senha"
            type="password"
            name="senha"
            autoComplete="current-password"
            placeholder="••••••••"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />

          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <Button type="submit" fullWidth isLoading={isSubmitting}>
            Entrar
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          Ainda não tem conta?{" "}
          <Link href="/register" className="font-medium text-brand-600 hover:text-brand-700">
            Criar conta
          </Link>
        </p>
      </div>
    </main>
  );
}

export default function LoginPage() {
  // `useSearchParams` exige uma fronteira de Suspense no App Router.
  return (
    <Suspense fallback={<FullPageLoader />}>
      <LoginForm />
    </Suspense>
  );
}
