/**
 * Ícones da navegação, em traço.
 *
 * Eram emoji — 📊 🤖 💬 🧪 🗂️ 📈. Emoji não é ilustração: ele é desenhado pelo
 * sistema operacional, muda de estilo entre Windows, Mac e Android, não herda
 * a cor do texto e não fica alinhado com a fonte ao lado. Numa barra lateral
 * escura, metade deles vinha com fundo branco próprio.
 *
 * Todos partem do mesmo grid de 24 e do mesmo traço de 1.75, que é o que faz
 * seis desenhos diferentes parecerem um conjunto.
 */

interface IconProps {
  className?: string;
}

function Base({ children, className }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {children}
    </svg>
  );
}

/** Visão geral: painel dividido. */
export function IconePainel(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </Base>
  );
}

/**
 * Agentes: os controles que se ajustam.
 *
 * A primeira versão era um robô — cabeça, antena e dois olhos. A 18px o rosto
 * fechava num borrão que parecia um cadeado, e a tela de Agentes é onde se
 * ajusta o prompt e os limites, não onde se conversa com um robô. Controles
 * dizem melhor o que a tela faz e sobrevivem ao tamanho.
 */
export function IconeAgente(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
      <circle cx="9" cy="7" r="2" fill="currentColor" stroke="none" />
      <circle cx="15" cy="12" r="2" fill="currentColor" stroke="none" />
      <circle cx="8" cy="17" r="2" fill="currentColor" stroke="none" />
    </Base>
  );
}

/** Atendimentos: a conversa. */
export function IconeConversa(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M20 15a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z" />
    </Base>
  );
}

/** Chat de teste: o ensaio antes de falar com gente de verdade. */
export function IconeTeste(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M9 3v6.5L4.6 17a2 2 0 0 0 1.7 3h11.4a2 2 0 0 0 1.7-3L15 9.5V3" />
      <path d="M8 3h8M8.2 13h7.6" />
    </Base>
  );
}

/** Kanban: as colunas do funil. */
export function IconeFunil(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="3" y="4" width="5.5" height="16" rx="1.5" />
      <rect x="9.25" y="4" width="5.5" height="11" rx="1.5" />
      <rect x="15.5" y="4" width="5.5" height="7" rx="1.5" />
    </Base>
  );
}

/** Métricas: a linha que sobe. */
export function IconeMetricas(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M3 20h18" />
      <path d="M6 16l4.5-5 3.5 3L20 7" />
      <path d="M20 11V7h-4" />
    </Base>
  );
}

/** Sair. */
export function IconeSair(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M15 4h2.5A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5H15" />
      <path d="M10 8l-4 4 4 4M6 12h9" />
    </Base>
  );
}
