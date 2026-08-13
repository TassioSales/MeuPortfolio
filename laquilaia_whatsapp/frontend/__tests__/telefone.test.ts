/**
 * Telefone: como mostrar e como abrir.
 *
 * O número chega do WhatsApp com DDI colado e sem separador. Estes casos
 * existem porque cada um deles já apareceu de verdade num número brasileiro.
 */

import { digitos, formatarTelefone, linkDoWhatsapp } from "@/lib/telefone";

describe("formatarTelefone", () => {
  it("formata celular com nove dígitos", () => {
    expect(formatarTelefone("5561999887234")).toBe("+55 61 99988-7234");
  });

  it("formata fixo com oito dígitos", () => {
    expect(formatarTelefone("556133334444")).toBe("+55 61 3333-4444");
  });

  it("não inventa formato para número estrangeiro", () => {
    // Quebrar um número de fora em grupos brasileiros o torna irreconhecível
    // para quem mora lá — pior que não formatar.
    expect(formatarTelefone("14155552671")).toBe("14155552671");
  });

  it("não quebra com número incompleto", () => {
    expect(formatarTelefone("5561")).toBe("5561");
    expect(formatarTelefone("")).toBe("");
  });

  it("preserva DDD 55, que não é DDI", () => {
    // Santa Maria/RS é DDD 55. Já houve um bug de arrancar o "55" da frente
    // achando que era o país e mutilar o número.
    expect(formatarTelefone("5555999887234")).toBe("+55 55 99988-7234");
  });
});

describe("linkDoWhatsapp", () => {
  it("monta o wa.me só com os dígitos", () => {
    expect(linkDoWhatsapp("+55 (61) 99988-7234")).toBe("https://wa.me/5561999887234");
  });

  it("não devolve link para número curto demais", () => {
    // `wa.me/` sem número abre uma página de erro do WhatsApp, o que é pior
    // que não ter link.
    expect(linkDoWhatsapp("123")).toBeNull();
    expect(linkDoWhatsapp("")).toBeNull();
  });
});

describe("digitos", () => {
  it("tira tudo que não é número", () => {
    expect(digitos("+55 (61) 9 9988-7234")).toBe("5561999887234");
  });
});
