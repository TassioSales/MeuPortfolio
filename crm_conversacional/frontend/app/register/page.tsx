"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthShell } from "@/components/AuthShell";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { useAuth } from "@/hooks/useAuth";

/** Mesmo mínimo exigido pelo backend em `UserCreate.senha`. */
const MIN_PASSWORD_LENGTH = 8;

export default function RegisterPage() {
  const router = useRouter();
  const { register, error, clearError } = useAuth();

  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearError();
    setLocalError(null);

    if (senha.length < MIN_PASSWORD_LENGTH) {
      setLocalError(`A senha precisa ter ao menos ${MIN_PASSWORD_LENGTH} caracteres.`);
      return;
    }

    if (senha !== confirmacao) {
      setLocalError("As senhas não conferem.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register(nome, email, senha);
      router.replace("/dashboard");
    } catch {
      setIsSubmitting(false);
    }
  }

  const shownError = localError ?? error;

  return (
    <AuthShell
      titulo="Criar conta"
      subtitulo="Comece a configurar o atendimento do escritório."
      rodape={
        <>
          Já tem conta?{" "}
          <Link href="/login" className="font-medium text-brand-600 hover:text-brand-700 dark:text-brand-200">
            Entrar
          </Link>
        </>
      }
    >
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-4 rounded-xl border border-surface-border bg-surface p-6 shadow-sm"
      >
        <Input
          label="Nome"
          name="nome"
          autoComplete="name"
          placeholder="Seu nome"
          required
          value={nome}
          onChange={(e) => setNome(e.target.value)}
        />

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
          autoComplete="new-password"
          placeholder="••••••••"
          required
          hint={`Mínimo de ${MIN_PASSWORD_LENGTH} caracteres.`}
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
        />

        <Input
          label="Confirmar senha"
          type="password"
          name="confirmacao"
          autoComplete="new-password"
          placeholder="••••••••"
          required
          value={confirmacao}
          onChange={(e) => setConfirmacao(e.target.value)}
        />

        {shownError && (
          <p role="alert" className="rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-700 dark:text-red-200">
            {shownError}
          </p>
        )}

        <Button type="submit" fullWidth isLoading={isSubmitting}>
          Criar conta
        </Button>
      </form>
    </AuthShell>
  );
}
