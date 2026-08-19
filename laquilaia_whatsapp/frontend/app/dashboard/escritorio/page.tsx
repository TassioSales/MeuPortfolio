"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { FullPageLoader } from "@/components/LoadingSpinner";
import { Textarea } from "@/components/Textarea";
import { messageFrom } from "@/hooks/useAgents";
import { useAuth } from "@/hooks/useAuth";
import { buscarEscritorio, salvarEscritorio } from "@/lib/escritorio";
import type { Escritorio } from "@/types";

const VAZIO: Escritorio = {
  nome: null,
  cnpj: null,
  oab_responsavel: null,
  fundador: null,
  endereco: null,
  email: null,
  telefone: null,
  telefone_suporte: null,
  horario_atendimento: null,
  site: null,
  instagram: null,
};

/**
 * Os dados do escritório, que o agente usa para responder.
 *
 * Antes disto o agente não sabia nada sobre o escritório que representa.
 * Perguntado "onde vocês ficam?", não tinha o que dizer — e o prompt manda
 * não inventar, então a conversa travava numa pergunta que qualquer
 * recepcionista responde.
 *
 * O campo que mais muda o atendimento não é o nome, é o **telefone do
 * suporte**: sem ele, quem já é cliente e escreve no comercial por engano
 * recomeça uma triagem do zero.
 */
export default function EscritorioPage() {
  const { user } = useAuth();
  const eAdmin = user?.papel === "admin";

  const [dados, setDados] = useState<Escritorio>(VAZIO);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [salvo, setSalvo] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await buscarEscritorio());
      setErro(null);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível carregar os dados do escritório."));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  function campo(nome: keyof Escritorio) {
    return {
      value: dados[nome] ?? "",
      onChange: (e: { target: { value: string } }) => {
        setDados((atual) => ({ ...atual, [nome]: e.target.value }));
        setSalvo(false);
      },
      disabled: !eAdmin,
    };
  }

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setSalvando(true);
    setErro(null);
    setSalvo(false);
    try {
      setDados(await salvarEscritorio(dados));
      setSalvo(true);
    } catch (e) {
      setErro(messageFrom(e, "Não foi possível salvar."));
    } finally {
      setSalvando(false);
    }
  }

  if (carregando) return <FullPageLoader label="Carregando..." />;

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-fg">Escritório</h1>
        <p className="mt-1 text-sm text-fg-muted">
          O que o agente responde quando perguntam sobre o escritório. Campo em
          branco é campo que ele não menciona — ele não inventa o que não sabe.
        </p>
      </header>

      {!eAdmin && (
        <p className="mb-4 rounded-lg border border-surface-border bg-surface-muted px-4 py-2.5 text-xs text-fg-soft">
          Só um administrador altera estes dados: eles mudam o que a IA diz a
          todo cliente. Você pode consultá-los — o telefone do suporte é o que
          você repassa a quem já é cliente do escritório.
        </p>
      )}

      <form onSubmit={enviar} className="flex flex-col gap-6">
        <fieldset className="rounded-xl border border-surface-border bg-surface p-5">
          <legend className="px-2 text-sm font-medium text-fg">Identificação</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Nome do escritório" maxLength={255} {...campo("nome")} />
            <Input label="CNPJ" maxLength={32} {...campo("cnpj")} />
            <Input label="OAB do responsável" maxLength={64} {...campo("oab_responsavel")} />
            <Input label="Fundador" maxLength={255} {...campo("fundador")} />
          </div>
        </fieldset>

        <fieldset className="rounded-xl border border-surface-border bg-surface p-5">
          <legend className="px-2 text-sm font-medium text-fg">Contato</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Telefone" maxLength={32} {...campo("telefone")} />
            <Input
              label="Telefone do suporte"
              maxLength={32}
              hint="Para quem já é cliente e escreveu no comercial por engano. Sem ele, o agente recomeça a triagem de quem já tem processo."
              {...campo("telefone_suporte")}
            />
            <Input label="E-mail" maxLength={255} {...campo("email")} />
            <Input
              label="Horário de atendimento"
              maxLength={255}
              placeholder="Seg a sex, 9h às 18h"
              {...campo("horario_atendimento")}
            />
          </div>
          <div className="mt-4">
            <Textarea label="Endereço" rows={2} maxLength={2000} {...campo("endereco")} />
          </div>
        </fieldset>

        <fieldset className="rounded-xl border border-surface-border bg-surface p-5">
          <legend className="px-2 text-sm font-medium text-fg">Presença digital</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Site" maxLength={255} {...campo("site")} />
            <Input label="Instagram" maxLength={255} placeholder="@escritorio" {...campo("instagram")} />
          </div>
        </fieldset>

        {erro && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-300">
            {erro}
          </p>
        )}
        {salvo && (
          <p role="status" className="text-sm text-green-700 dark:text-green-300">
            Salvo. O agente já usa estes dados na próxima mensagem.
          </p>
        )}

        {eAdmin && (
          <div className="flex justify-end">
            <Button type="submit" isLoading={salvando}>
              Salvar
            </Button>
          </div>
        )}
      </form>
    </div>
  );
}
