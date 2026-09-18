// O JID da Evolution traz o telefone só com dígitos (ex: 5511998877665), sem "+".
//
// Validar o formato importa porque este valor vai direto para o campo `to` da
// API de envio: é o que impede transformar o bot em relay de mensagem para um
// destino arbitrário. Fica em um módulo próprio porque a mesma regra é aplicada
// em três lugares (webhook, aviso de indisponibilidade e script de retenção) e
// três cópias da regex viravam três chances de divergir.
const TELEFONE_VALIDO = /^\d{6,20}$/;

export function ehTelefoneValido(valor: unknown): valor is string {
  return typeof valor === 'string' && TELEFONE_VALIDO.test(valor);
}
