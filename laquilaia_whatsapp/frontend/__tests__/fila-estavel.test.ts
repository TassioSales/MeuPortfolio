/**
 * A fila de atendimentos não se mexe embaixo de quem está trabalhando nela.
 *
 * O servidor devolve a fila da mensagem mais recente para a mais antiga, e
 * isso está certo. O que estava errado era o efeito colateral: a **resposta do
 * próprio operador** é uma mensagem nova, então cada frase que ele digitava
 * recarregava a fila e fazia a conversa aberta pular para o topo — a lista
 * andando sozinha enquanto ele lia.
 */

import { aplicarOrdemCongelada } from "@/hooks/useConversations";
import type { ConversationSummary } from "@/types";

function conversa(id: string): ConversationSummary {
  return {
    id,
    phone_number: `5561${id}`,
    status: "ativa",
    ia_ativa: true,
    lead_nome: id,
    lead_status_funil: "novo",
    data_ultima_msg: "2026-08-19T10:00:00",
    total_mensagens: 1,
    ultima_mensagem: "oi",
    ultimo_remetente: "user",
  };
}

const ids = (lista: ConversationSummary[]) => lista.map((c) => c.id);

describe("ordem da fila", () => {
  it("sem conversa aberta, a ordem do servidor passa direto", () => {
    // Quem não está lendo nada quer a fila atualizada: o cliente que acabou
    // de escrever precisa aparecer em cima.
    const vindas = [conversa("c"), conversa("a"), conversa("b")];

    expect(ids(aplicarOrdemCongelada(vindas, null))).toEqual(["c", "a", "b"]);
  });

  it("com conversa aberta, a fila fica parada mesmo que o servidor reordene", () => {
    const congelada = ["a", "b", "c"];
    // O servidor agora põe "b" em primeiro: foi nela que o operador escreveu.
    const vindas = [conversa("b"), conversa("a"), conversa("c")];

    expect(ids(aplicarOrdemCongelada(vindas, congelada))).toEqual(["a", "b", "c"]);
  });

  it("conversa que sumiu do servidor some da tela", () => {
    const vindas = [conversa("a"), conversa("c")];

    expect(ids(aplicarOrdemCongelada(vindas, ["a", "b", "c"]))).toEqual(["a", "c"]);
  });

  it("conversa nova aparece no topo, não escondida no fim", () => {
    // Congelar a ordem não pode virar esconder quem chegou agora — é
    // exatamente para isso que a fila existe.
    const vindas = [conversa("nova"), conversa("a"), conversa("b")];

    expect(ids(aplicarOrdemCongelada(vindas, ["a", "b"]))).toEqual(["nova", "a", "b"]);
  });

  it("duas conversas novas mantêm entre si a ordem do servidor", () => {
    const vindas = [conversa("nova2"), conversa("nova1"), conversa("a")];

    expect(ids(aplicarOrdemCongelada(vindas, ["a"]))).toEqual(["nova2", "nova1", "a"]);
  });

  it("não modifica o array que recebeu", () => {
    // O `sort` do JS ordena no lugar; sem a cópia isto embaralharia o estado
    // de quem chamou.
    const vindas = [conversa("b"), conversa("a")];

    aplicarOrdemCongelada(vindas, ["a", "b"]);

    expect(ids(vindas)).toEqual(["b", "a"]);
  });
});
