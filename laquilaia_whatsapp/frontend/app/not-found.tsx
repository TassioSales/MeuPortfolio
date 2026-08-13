import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-5xl font-semibold text-brand-600">404</p>
      <h1 className="text-xl font-semibold text-gray-900">Página não encontrada</h1>
      <p className="max-w-sm text-sm text-gray-600">
        O endereço acessado não existe ou foi movido.
      </p>
      <Link
        href="/dashboard"
        className="rounded-lg bg-ink-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-ink-800"
      >
        Voltar ao dashboard
      </Link>
    </main>
  );
}
