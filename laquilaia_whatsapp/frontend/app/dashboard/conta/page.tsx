"use client";

import { useState } from "react";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { messageFrom } from "@/hooks/useAgents";
import { useAuth } from "@/hooks/useAuth";
import { trocarMinhaSenha } from "@/lib/usuarios";

const SENHA_MINIMA = 8;

export default function ContaPage() {
  const { user } = useAuth();

  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [pronto, setPronto] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setPronto(false);

    // Conferido aqui e não só no backend: o backend não recebe a confirmação,
    // e quem digita errado duas vezes trocaria a senha para algo que não sabe.
    if (nova !== confirmacao) {
      setErro("A nova senha e a confirmação não são iguais.");
      return;
    }

    setSalvando(true);
    try {
      await trocarMinhaSenha({ senha_atual: atual, senha_nova: nova });
      setAtual("");
      setNova("");
      setConfirmacao("");
      setPronto(true);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível trocar a senha."));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-fg">Minha conta</h1>
        {user && (
          <p className="mt-1 text-sm text-fg-muted">
            {user.nome} · {user.email} ·{" "}
            {user.papel === "admin" ? "administrador" : "operador"}
          </p>
        )}
      </header>

      <form
        onSubmit={enviar}
        className="flex flex-col gap-4 rounded-xl border border-surface-border bg-surface p-5"
      >
        <h2 className="text-sm font-medium text-fg">Trocar a senha</h2>

        <Input
          label="Senha atual"
          type="password"
          autoComplete="current-password"
          value={atual}
          onChange={(e) => setAtual(e.target.value)}
          required
          hint="Pedida mesmo com a sessão aberta: um navegador esquecido aberto não pode virar troca de senha."
        />
        <Input
          label="Nova senha"
          type="password"
          autoComplete="new-password"
          value={nova}
          onChange={(e) => setNova(e.target.value)}
          required
          minLength={SENHA_MINIMA}
        />
        <Input
          label="Repita a nova senha"
          type="password"
          autoComplete="new-password"
          value={confirmacao}
          onChange={(e) => setConfirmacao(e.target.value)}
          required
          minLength={SENHA_MINIMA}
        />

        {erro && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-300">
            {erro}
          </p>
        )}
        {pronto && (
          <p role="status" className="text-sm text-green-700 dark:text-green-300">
            Senha trocada. A sessão aberta continua valendo; o próximo login usa a nova.
          </p>
        )}

        <Button type="submit" isLoading={salvando}>
          Trocar senha
        </Button>
      </form>

      {user?.papel !== "admin" && (
        <p className="mt-4 text-xs text-fg-muted">
          Esqueceu a senha? Só um administrador resolve — ele cria um acesso
          novo. Ninguém, nem o administrador, troca a senha de outra pessoa.
        </p>
      )}
    </div>
  );
}
