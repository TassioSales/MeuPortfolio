"use client";

import { useState, type FormEvent } from "react";
import { Button } from "./Button";
import { Input } from "./Input";
import { Textarea } from "./Textarea";
import { messageFrom } from "@/hooks/useAgents";
import { AGENT_LIMITS, type Agent, type AgentInput } from "@/types";

interface AgentFormProps {
  /** Ausente = criação; presente = edição. */
  agent?: Agent;
  onSubmit: (data: AgentInput) => Promise<void>;
  onCancel: () => void;
}

const DEFAULT_TEMPERATURA = 0.7;
const DEFAULT_MAX_TOKENS = 1024;

type FieldErrors = Partial<Record<keyof AgentInput, string>>;

function toNumber(value: string): number {
  return value.trim() === "" ? Number.NaN : Number(value);
}

/**
 * Repete as regras de `agent_service.create_agent` para dar retorno imediato.
 * O backend continua sendo a autoridade — isto é só conveniência de UI.
 */
function validate(data: AgentInput): FieldErrors {
  const errors: FieldErrors = {};

  if (!data.nome.trim()) {
    errors.nome = "Informe um nome para o agente.";
  } else if (data.nome.length > AGENT_LIMITS.nomeMaxLength) {
    errors.nome = `O nome deve ter no máximo ${AGENT_LIMITS.nomeMaxLength} caracteres.`;
  }

  if (!data.system_prompt.trim()) {
    errors.system_prompt = "O system prompt não pode ficar vazio.";
  }

  if (
    Number.isNaN(data.temperatura) ||
    data.temperatura < AGENT_LIMITS.temperaturaMin ||
    data.temperatura > AGENT_LIMITS.temperaturaMax
  ) {
    errors.temperatura = `A temperatura deve estar entre ${AGENT_LIMITS.temperaturaMin} e ${AGENT_LIMITS.temperaturaMax}.`;
  }

  if (
    !Number.isInteger(data.max_tokens) ||
    data.max_tokens < AGENT_LIMITS.maxTokensMin ||
    data.max_tokens > AGENT_LIMITS.maxTokensMax
  ) {
    errors.max_tokens = `Informe um inteiro entre ${AGENT_LIMITS.maxTokensMin} e ${AGENT_LIMITS.maxTokensMax}.`;
  }

  return errors;
}

export function AgentForm({ agent, onSubmit, onCancel }: AgentFormProps) {
  const [nome, setNome] = useState(agent?.nome ?? "");
  const [descricao, setDescricao] = useState(agent?.descricao ?? "");
  const [systemPrompt, setSystemPrompt] = useState(agent?.system_prompt ?? "");
  const [temperatura, setTemperatura] = useState(
    String(agent?.temperatura ?? DEFAULT_TEMPERATURA),
  );
  const [maxTokens, setMaxTokens] = useState(
    String(agent?.max_tokens ?? DEFAULT_MAX_TOKENS),
  );
  const [anexos, setAnexos] = useState(agent?.anexos_habilitados ?? false);

  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    const data: AgentInput = {
      nome: nome.trim(),
      descricao: descricao.trim() || null,
      system_prompt: systemPrompt,
      // Campo vazio precisa virar NaN: `Number("")` é 0, o que passaria
      // silenciosamente um valor que o usuário não escolheu.
      temperatura: toNumber(temperatura),
      max_tokens: toNumber(maxTokens),
      anexos_habilitados: anexos,
    };

    const errors = validate(data);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);
    try {
      await onSubmit(data);
    } catch (error) {
      setSubmitError(messageFrom(error, "Não foi possível salvar o agente."));
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <Input
        label="Nome"
        name="nome"
        placeholder="Ex: Qualificador de leads"
        required
        value={nome}
        onChange={(e) => setNome(e.target.value)}
        error={fieldErrors.nome}
      />

      <Input
        label="Descrição (opcional)"
        name="descricao"
        placeholder="Para que serve este agente"
        value={descricao}
        onChange={(e) => setDescricao(e.target.value)}
      />

      <Textarea
        label="System prompt"
        name="system_prompt"
        placeholder="Você é um assistente que qualifica leads via WhatsApp..."
        required
        value={systemPrompt}
        onChange={(e) => setSystemPrompt(e.target.value)}
        error={fieldErrors.system_prompt}
        hint="Instruções de comportamento enviadas ao Claude em toda conversa."
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Temperatura"
          name="temperatura"
          type="number"
          step="0.1"
          min={AGENT_LIMITS.temperaturaMin}
          max={AGENT_LIMITS.temperaturaMax}
          value={temperatura}
          onChange={(e) => setTemperatura(e.target.value)}
          error={fieldErrors.temperatura}
          hint="0 = determinístico, 2 = mais criativo."
        />

        <Input
          label="Max tokens"
          name="max_tokens"
          type="number"
          step="1"
          min={AGENT_LIMITS.maxTokensMin}
          max={AGENT_LIMITS.maxTokensMax}
          value={maxTokens}
          onChange={(e) => setMaxTokens(e.target.value)}
          error={fieldErrors.max_tokens}
          hint="Tamanho máximo da resposta."
        />
      </div>

      <label className="flex items-start gap-3 rounded-lg border border-surface-border p-3">
        <input
          type="checkbox"
          name="anexos_habilitados"
          checked={anexos}
          onChange={(e) => setAnexos(e.target.checked)}
          className="mt-0.5 h-4 w-4 shrink-0 accent-ink-900"
        />
        <span>
          <span className="block text-sm font-medium text-fg">
            Ler anexos do cliente
          </span>
          <span className="mt-0.5 block text-xs text-fg-muted">
            Imagem, PDF e áudio — a foto da carta de demissão, o contrato, o
            áudio de quem prefere falar. Cada anexo é uma chamada a mais à
            Evolution e tokens a mais no modelo. Desligado, o agente pede que a
            pessoa escreva.
          </span>
        </span>
      </label>

      {submitError && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {submitError}
        </p>
      )}

      <div className="mt-2 flex justify-end gap-3">
        <Button type="button" variant="secondary" onClick={onCancel} disabled={isSubmitting}>
          Cancelar
        </Button>
        <Button type="submit" isLoading={isSubmitting}>
          {agent ? "Salvar alterações" : "Criar agente"}
        </Button>
      </div>
    </form>
  );
}

export default AgentForm;
