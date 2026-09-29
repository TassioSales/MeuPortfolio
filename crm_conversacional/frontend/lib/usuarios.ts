/**
 * Acessos ao painel — quem entra, com qual papel.
 *
 * Endpoints de `backend/app/routers/auth.py`. Tudo aqui, menos a troca da
 * própria senha, exige administrador; o backend responde **404** a quem não é
 * (e não 403, para não confirmar que a rota existe).
 */

import { api } from "./api";
import type { AlteracaoDeAcesso, NovoAcesso, TrocaDeSenha, User } from "@/types";

const USERS = "/api/v1/auth/users";
const PASSWORD = "/api/v1/auth/password";

export async function listarAcessos(): Promise<User[]> {
  return api.get<User[]>(USERS);
}

export async function criarAcesso(dados: NovoAcesso): Promise<User> {
  return api.post<User>(USERS, dados);
}

export async function alterarAcesso(
  userId: string,
  dados: AlteracaoDeAcesso,
): Promise<User> {
  return api.patch<User>(`${USERS}/${userId}`, dados);
}

/** Responde 204; o retorno é `void` de propósito. */
export async function trocarMinhaSenha(dados: TrocaDeSenha): Promise<void> {
  await api.post<void>(PASSWORD, dados);
}
