"use client";

import { ConexaoWhatsapp } from "@/components/ConexaoWhatsapp";

export default function WhatsappPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-fg">WhatsApp</h1>
        <p className="mt-1 text-sm text-fg-muted">
          O número que atende. Enquanto ele estiver desconectado, nenhuma
          mensagem chega ao agente.
        </p>
      </header>

      <ConexaoWhatsapp />
    </div>
  );
}
