import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { ACCESS_TOKEN_KEY, DEFAULT_AUTHENTICATED_ROUTE } from "@/lib/constants";

/**
 * Raiz do site: manda para o dashboard quem já tem sessão, senão para o login.
 * A validade do token é conferida depois, no `loadSession()` do dashboard.
 */
export default function HomePage() {
  const hasSession = cookies().get(ACCESS_TOKEN_KEY) !== undefined;
  redirect(hasSession ? DEFAULT_AUTHENTICATED_ROUTE : "/login");
}
