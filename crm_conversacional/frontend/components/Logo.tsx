/**
 * A marca do AdvogAi.
 *
 * O símbolo é um "A" cujo travessão atravessa a letra e sai dos dois lados,
 * com um peso em cada ponta: é a letra e é uma balança, na mesma forma. Foi
 * essa a escolha — não uma balança desenhada ao lado do nome, que é o que todo
 * escritório usa, e não um martelo, que nem se usa no foro brasileiro.
 *
 * Desenhado em traço, sem preenchimento, para continuar legível a 20px na
 * barra lateral: forma cheia vira borrão nesse tamanho. As duas cores separam
 * o que é letra do que é balança — o peso em latão é o único ponto quente da
 * interface inteira, e é onde o olho cai.
 */

import { cn } from "@/lib/utils";

interface MarcaProps {
  className?: string;
  /** Tamanho em px do lado do quadrado. */
  size?: number;
}

export function Marca({ className, size = 28 }: MarcaProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      width={size}
      height={size}
      fill="none"
      role="img"
      aria-label="AdvogAi"
      className={cn("shrink-0", className)}
    >
      {/* As duas pernas do A. O ápice arredondado tira o ar de brasão. */}
      <path
        d="M9.4 25.6 L16 6.8 L22.6 25.6"
        stroke="currentColor"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* O travessão, que passa direto e vira o braço da balança. */}
      <path
        d="M5.2 19.4 H26.8"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        opacity="0.9"
      />
      {/* Os pratos. Círculo cheio em vez de concha: a concha some a 20px. */}
      <circle cx="5.2" cy="19.4" r="2.4" className="fill-brass-400" />
      <circle cx="26.8" cy="19.4" r="2.4" className="fill-brass-400" />
    </svg>
  );
}

interface LogoProps {
  className?: string;
  size?: number;
  /** Sem o nome escrito — para espaços apertados. */
  soMarca?: boolean;
}

/**
 * Marca + nome.
 *
 * O nome é uma palavra só, com o "A" do meio em maiúscula: `AdvogAi`. O
 * destaque em latão cai sobre o `Ai` porque é onde está a junção — advocacia e
 * IA — e porque é o que diferencia o nome de mais um escritório.
 */
export function Logo({ className, size = 28, soMarca = false }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Marca size={size} />
      {!soMarca && (
        <span className="text-[1.0625rem] font-semibold tracking-tight">
          Advog<span className="text-brass-400">Ai</span>
        </span>
      )}
    </span>
  );
}

export default Logo;
