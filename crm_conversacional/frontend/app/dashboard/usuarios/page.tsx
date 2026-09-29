"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Input } from "@/components/Input";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { Modal } from "@/components/Modal";
import { useAuth } from "@/hooks/useAuth";
import { messageFrom } from "@/hooks/useAgents";
import { alterarAcesso, criarAcesso, listarAcessos } from "@/lib/usuarios";
import type { Papel, User } from "@/types";

const SENHA_MINIMA = 8;
const FALHA = "Não foi possível concluir a operação.";

const DESCRICAO_DO_PAPEL: Record<Papel, string> = {
  admin: "Configura agentes, WhatsApp e acessos. Vê tudo.",
  operador: "Atende: conversas, Kanban e métricas. Não configura nada.",
};

export default function UsuariosPage() {
  const { user: eu } = useAuth();
  const [acessos, setAcessos] = useState<User[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [criando, setCriando] = useState(false);
  // Um id por vez: é o acesso cujo botão está esperando o servidor.
  const [emCurso, setEmCurso] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setAcessos(await listarAcessos());
    } catch (e) {
      setErro(messageFrom(e, FALHA));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  async function mudar(alvo: User, dados: { papel?: Papel; status?: "ativo" | "inativo" }) {
    setEmCurso(alvo.id);
    setErro(null);
    try {
      const atualizado = await alterarAcesso(alvo.id, dados);
      setAcessos((atual) => atual.map((u) => (u.id === atualizado.id ? atualizado : u)));
    } catch (e) {
      setErro(messageFrom(e, FALHA));
    } finally {
      setEmCurso(null);
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-fg">Acessos</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Quem entra no painel e o que cada um pode fazer. Ninguém se cadastra
            sozinho: os acessos nascem aqui.
          </p>
        </div>
        <Button onClick={() => setCriando(true)}>Novo acesso</Button>
      </header>

      {erro && (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          {erro}
        </p>
      )}

      {carregando ? (
        <FullPageLoader label="Carregando acessos..." />
      ) : acessos.length === 0 ? (
        <EmptyState
          icon="👥"
          title="Nenhum acesso"
          description="Crie o primeiro acesso para alguém do escritório."
          action={<Button onClick={() => setCriando(true)}>Criar acesso</Button>}
        />
      ) : (
        <ul className="divide-y divide-surface-border overflow-hidden rounded-xl border border-surface-border bg-surface">
          {acessos.map((acesso) => {
            const souEu = acesso.id === eu?.id;
            const inativo = acesso.status !== "ativo";
            const ocupado = emCurso === acesso.id;

            return (
              <li
                key={acesso.id}
                className="flex flex-wrap items-center justify-between gap-4 px-5 py-4"
              >
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-sm font-medium text-fg">
                    <span className="truncate">{acesso.nome}</span>
                    {souEu && (
                      <span className="rounded bg-surface-muted px-1.5 py-0.5 text-[11px] font-normal text-fg-muted">
                        você
                      </span>
                    )}
                    {inativo && (
                      <span className="rounded bg-red-100 px-1.5 py-0.5 text-[11px] font-normal text-red-700 dark:bg-red-950/60 dark:text-red-200">
                        inativo
                      </span>
                    )}
                  </p>
                  <p className="truncate text-xs text-fg-muted">{acesso.email}</p>
                  <p className="mt-1 text-xs text-fg-faint">
                    {DESCRICAO_DO_PAPEL[acesso.papel] ?? acesso.papel}
                  </p>
                </div>

                {/* Sobre mim mesmo não há botão nenhum: o backend recusa que o
                    administrador se rebaixe ou se desative, e um botão que só
                    serve para mostrar um erro não é um botão. */}
                {souEu ? (
                  <span className="text-xs text-fg-faint">administrador desta conta</span>
                ) : (
                  <div className="flex shrink-0 items-center gap-2">
                    <Button
                      variant="secondary"
                      isLoading={ocupado}
                      onClick={() =>
                        void mudar(acesso, {
                          papel: acesso.papel === "admin" ? "operador" : "admin",
                        })
                      }
                    >
                      {acesso.papel === "admin" ? "Tornar operador" : "Tornar admin"}
                    </Button>
                    <Button
                      variant={inativo ? "secondary" : "danger"}
                      isLoading={ocupado}
                      onClick={() =>
                        void mudar(acesso, { status: inativo ? "ativo" : "inativo" })
                      }
                    >
                      {inativo ? "Reativar" : "Desativar"}
                    </Button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <p className="mt-4 text-xs text-fg-muted">
        Desativar vale na hora: a sessão que a pessoa já tem aberta para de
        funcionar na requisição seguinte.
      </p>

      <FormularioDeAcesso
        aberto={criando}
        onFechar={() => setCriando(false)}
        onCriado={(novo) => {
          setAcessos((atual) => [...atual, novo]);
          setCriando(false);
        }}
      />
    </div>
  );
}

function FormularioDeAcesso({
  aberto,
  onFechar,
  onCriado,
}: {
  aberto: boolean;
  onFechar: () => void;
  onCriado: (novo: User) => void;
}) {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [papel, setPapel] = useState<Papel>("operador");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function fechar() {
    setNome("");
    setEmail("");
    setSenha("");
    setPapel("operador");
    setErro(null);
    onFechar();
  }

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setSalvando(true);
    setErro(null);
    try {
      const novo = await criarAcesso({ nome, email, senha, papel });
      onCriado(novo);
      setNome("");
      setEmail("");
      setSenha("");
      setPapel("operador");
    } catch (e) {
      setErro(messageFrom(e, FALHA));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal
      isOpen={aberto}
      onClose={fechar}
      title="Novo acesso"
      description="A senha é combinada aqui e entregue à pessoa. Ela troca depois em Minha conta."
    >
      <form onSubmit={enviar} className="flex flex-col gap-4">
        <Input
          label="Nome"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          required
          maxLength={255}
        />
        <Input
          label="E-mail"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Input
          label="Senha inicial"
          type="text"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          required
          minLength={SENHA_MINIMA}
          hint={`Pelo menos ${SENHA_MINIMA} caracteres. Fica visível porque quem digita é quem vai entregá-la.`}
        />

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-medium text-fg-soft">Papel</legend>
          {(["operador", "admin"] as Papel[]).map((opcao) => (
            <label
              key={opcao}
              className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-surface-border bg-surface p-3"
            >
              <input
                type="radio"
                name="papel"
                className="mt-0.5 bg-surface"
                checked={papel === opcao}
                onChange={() => setPapel(opcao)}
              />
              <span>
                <span className="block text-sm font-medium text-fg">
                  {opcao === "admin" ? "Administrador" : "Operador"}
                </span>
                <span className="block text-xs text-fg-muted">
                  {DESCRICAO_DO_PAPEL[opcao]}
                </span>
              </span>
            </label>
          ))}
        </fieldset>

        {erro && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-300">
            {erro}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={fechar}>
            Cancelar
          </Button>
          <Button type="submit" isLoading={salvando}>
            Criar acesso
          </Button>
        </div>
      </form>
    </Modal>
  );
}
