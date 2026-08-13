/**
 * Testes do formulário de agente: validação no cliente e envio.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AgentForm } from "@/components/AgentForm";
import type { Agent } from "@/types";

const AGENT: Agent = {
  id: "agent-1",
  user_id: "user-1",
  nome: "Qualificador",
  descricao: "Qualifica leads",
  system_prompt: "Você é um assistente...",
  temperatura: 0.7,
  max_tokens: 1024,
  anexos_habilitados: false,
  status: "ativo",
  data_criacao: "2026-08-11T00:00:00Z",
  data_atualizacao: "2026-08-11T00:00:00Z",
};

describe("AgentForm", () => {
  it("preenche os campos ao editar um agente existente", () => {
    render(<AgentForm agent={AGENT} onSubmit={jest.fn()} onCancel={jest.fn()} />);

    expect(screen.getByLabelText("Nome")).toHaveValue("Qualificador");
    expect(screen.getByLabelText("System prompt")).toHaveValue("Você é um assistente...");
    expect(screen.getByLabelText("Temperatura")).toHaveValue(0.7);
    expect(screen.getByLabelText("Max tokens")).toHaveValue(1024);
    expect(screen.getByRole("button", { name: "Salvar alterações" })).toBeInTheDocument();
  });

  it("usa os padrões do backend na criação", () => {
    render(<AgentForm onSubmit={jest.fn()} onCancel={jest.fn()} />);

    expect(screen.getByLabelText("Temperatura")).toHaveValue(0.7);
    expect(screen.getByLabelText("Max tokens")).toHaveValue(1024);
    expect(screen.getByRole("button", { name: "Criar agente" })).toBeInTheDocument();
  });

  it("envia os dados normalizados, com descrição vazia virando null", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(<AgentForm onSubmit={onSubmit} onCancel={jest.fn()} />);

    await user.type(screen.getByLabelText("Nome"), "  Novo agente  ");
    await user.type(screen.getByLabelText("System prompt"), "Instruções");
    await user.click(screen.getByRole("button", { name: "Criar agente" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({
      nome: "Novo agente",
      descricao: null,
      system_prompt: "Instruções",
      temperatura: 0.7,
      max_tokens: 1024,
      // Desligado por padrão: ninguém liga leitura de documento sem saber, e
      // cada anexo custa uma chamada à Evolution e tokens no modelo.
      anexos_habilitados: false,
    });
  });

  it("a leitura de anexos é uma escolha, e vem desligada", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(<AgentForm onSubmit={onSubmit} onCancel={jest.fn()} />);

    const chave = screen.getByLabelText(/Ler anexos do cliente/);
    expect(chave).not.toBeChecked();

    await user.type(screen.getByLabelText("Nome"), "Triagem");
    await user.type(screen.getByLabelText("System prompt"), "Instruções");
    await user.click(chave);
    await user.click(screen.getByRole("button", { name: "Criar agente" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ anexos_habilitados: true }),
    );
  });

  it("bloqueia o envio quando o system prompt só tem espaços", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(<AgentForm onSubmit={onSubmit} onCancel={jest.fn()} />);

    await user.type(screen.getByLabelText("Nome"), "Agente");
    await user.type(screen.getByLabelText("System prompt"), "   ");
    await user.click(screen.getByRole("button", { name: "Criar agente" }));

    expect(await screen.findByText("O system prompt não pode ficar vazio.")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  /**
   * Valores fora da faixa são barrados pelo próprio navegador: os inputs
   * carregam `min`/`max`, então a validação de constraint do HTML impede o
   * submit e `handleSubmit` nem chega a rodar. O que importa garantir é que
   * o valor inválido nunca chega ao backend.
   */
  it("não envia temperatura acima do limite do backend", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(<AgentForm onSubmit={onSubmit} onCancel={jest.fn()} />);

    await user.type(screen.getByLabelText("Nome"), "Agente");
    await user.type(screen.getByLabelText("System prompt"), "Instruções");
    const temperatura = screen.getByLabelText("Temperatura");
    fireEvent.change(temperatura, { target: { value: "3" } });
    await user.click(screen.getByRole("button", { name: "Criar agente" }));

    expect((temperatura as HTMLInputElement).checkValidity()).toBe(false);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("não envia max tokens acima de 4096", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(<AgentForm onSubmit={onSubmit} onCancel={jest.fn()} />);

    await user.type(screen.getByLabelText("Nome"), "Agente");
    await user.type(screen.getByLabelText("System prompt"), "Instruções");
    const maxTokens = screen.getByLabelText("Max tokens");
    fireEvent.change(maxTokens, { target: { value: "9999" } });
    await user.click(screen.getByRole("button", { name: "Criar agente" }));

    expect((maxTokens as HTMLInputElement).checkValidity()).toBe(false);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  /**
   * Campo numérico vazio passa pela validação do navegador (não é `required`),
   * então quem barra é a validação em JS — sem ela `Number("")` viraria 0 e
   * enviaria um valor que o usuário não escolheu.
   */
  it("bloqueia temperatura vazia em vez de enviar 0 silenciosamente", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(<AgentForm onSubmit={onSubmit} onCancel={jest.fn()} />);

    await user.type(screen.getByLabelText("Nome"), "Agente");
    await user.type(screen.getByLabelText("System prompt"), "Instruções");
    await user.clear(screen.getByLabelText("Temperatura"));
    await user.click(screen.getByRole("button", { name: "Criar agente" }));

    expect(await screen.findByText(/temperatura deve estar entre 0 e 2/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("bloqueia max tokens vazio", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn();
    render(<AgentForm onSubmit={onSubmit} onCancel={jest.fn()} />);

    await user.type(screen.getByLabelText("Nome"), "Agente");
    await user.type(screen.getByLabelText("System prompt"), "Instruções");
    await user.clear(screen.getByLabelText("Max tokens"));
    await user.click(screen.getByRole("button", { name: "Criar agente" }));

    expect(await screen.findByText(/inteiro entre 1 e 4096/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("mostra o erro do backend quando o envio falha", async () => {
    const user = userEvent.setup();
    const onSubmit = jest.fn().mockRejectedValue(new Error("Temperature must be between 0 and 2"));
    render(<AgentForm onSubmit={onSubmit} onCancel={jest.fn()} />);

    await user.type(screen.getByLabelText("Nome"), "Agente");
    await user.type(screen.getByLabelText("System prompt"), "Instruções");
    await user.click(screen.getByRole("button", { name: "Criar agente" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Temperature must be between 0 and 2",
    );
  });

  it("cancelar não dispara o envio", async () => {
    const user = userEvent.setup();
    const onCancel = jest.fn();
    const onSubmit = jest.fn();
    render(<AgentForm onSubmit={onSubmit} onCancel={onCancel} />);

    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
