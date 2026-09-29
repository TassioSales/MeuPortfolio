// Bug REAL que esta ferramenta NÃO pega, mantido aqui para que a limitação fique testada.
//
// Com telefone vazio a função devolve "@sms.cal.com": uma string válida, do tipo declarado, sem
// "undefined" e sem "NaN". Nenhuma das três regras se aplica. Detectar isto exigiria saber que o
// resultado precisa identificar alguém, e esse conhecimento não está na assinatura.

/** Telefone sem dígito devolve um endereço que serve para qualquer um. */
export function emailFromPhone(phoneNumber: string): string {
  return `${phoneNumber.replace(/\+/g, "")}@sms.cal.com`;
}
