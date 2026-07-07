"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/authStore";

type Mode = "login" | "register";

const SKILLS = ["Python", "SQL", "JavaScript", "Go", "Docker", "AWS", "React", "FastAPI", "Git", "Linux"];

const DEMO = {
  email: "demo@trilha.app",
  password: "demo123",
};

export default function LoginPage() {
  const router = useRouter();
  const { setToken, loadUser } = useAuthStore();
  const [mode, setMode] = useState<Mode>("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);

  const [form, setForm] = useState({
    email: DEMO.email,
    password: DEMO.password,
    name: "",
    current_role: "",
    target_role: "",
    experience_years: "0",
  });

  function toggleSkill(s: string) {
    setSelectedSkills((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  }

  function validate(): boolean {
    const errs: Record<string, string> = {};
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRe.test(form.email)) errs.email = "Email inválido.";
    if (form.password.length < 6) errs.password = "Senha deve ter ao menos 6 caracteres.";
    if (mode === "register") {
      if (!form.name.trim()) errs.name = "Nome obrigatório.";
      if (!form.current_role.trim()) errs.current_role = "Cargo atual obrigatório.";
      if (!form.target_role.trim()) errs.target_role = "Meta de carreira obrigatória.";
    }
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    setError("");
    try {
      let token: string;
      if (mode === "login") {
        const r = await api.auth.login(form.email, form.password);
        token = r.access_token;
      } else {
        const r = await api.auth.register({
          ...form,
          experience_years: parseInt(form.experience_years),
          known_skills: selectedSkills,
        });
        token = r.access_token;
      }
      setToken(token);
      await loadUser();
      router.push("/dashboard");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-2">
            <TrendingUp className="text-accent" size={28} />
            <span className="text-2xl font-bold text-text-primary tracking-tight">TRILHA</span>
          </div>
          <p className="text-text-muted text-sm">Sua trilha de carreira com IA</p>
        </div>

        <div className="bg-surface-raised border border-border rounded-2xl p-6">
          {/* Tabs */}
          <div className="flex gap-2 mb-5">
            {(["login", "register"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(""); }}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                  mode === m
                    ? "bg-accent text-surface"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                {m === "login" ? "Entrar" : "Criar conta"}
              </button>
            ))}
          </div>

          {/* Demo hint */}
          {mode === "login" && (
            <div className="mb-4 px-3 py-2.5 bg-accent/8 border border-accent/20 rounded-lg flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-accent">Credenciais de demonstração</p>
                <p className="text-xs text-text-muted mt-0.5">
                  {DEMO.email} / {DEMO.password}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, email: DEMO.email, password: DEMO.password }))}
                className="text-xs px-2.5 py-1 bg-accent text-surface rounded-md font-semibold hover:bg-accent-dim transition-colors"
              >
                Preencher
              </button>
            </div>
          )}

          <form onSubmit={submit} className="space-y-3">
            {mode === "register" && (
              <div>
                <input
                  placeholder="Nome completo"
                  value={form.name}
                  onChange={(e) => { setForm({ ...form, name: e.target.value }); setFieldErrors((fe) => ({ ...fe, name: "" })); }}
                  className={`w-full bg-surface border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent/60 transition-colors ${fieldErrors.name ? "border-red-400" : "border-border"}`}
                />
                {fieldErrors.name && <p className="text-xs text-red-400 mt-1 px-1">{fieldErrors.name}</p>}
              </div>
            )}

            <div>
              <input
                type="email"
                placeholder="Email"
                value={form.email}
                onChange={(e) => { setForm({ ...form, email: e.target.value }); setFieldErrors((fe) => ({ ...fe, email: "" })); }}
                className={`w-full bg-surface border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent/60 transition-colors ${fieldErrors.email ? "border-red-400" : "border-border"}`}
              />
              {fieldErrors.email && <p className="text-xs text-red-400 mt-1 px-1">{fieldErrors.email}</p>}
            </div>

            <div>
              <input
                type="password"
                placeholder="Senha"
                value={form.password}
                onChange={(e) => { setForm({ ...form, password: e.target.value }); setFieldErrors((fe) => ({ ...fe, password: "" })); }}
                className={`w-full bg-surface border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent/60 transition-colors ${fieldErrors.password ? "border-red-400" : "border-border"}`}
              />
              {fieldErrors.password && <p className="text-xs text-red-400 mt-1 px-1">{fieldErrors.password}</p>}
            </div>

            {mode === "register" && (
              <>
                <div>
                  <input
                    placeholder="Cargo atual (ex: Data Analyst)"
                    value={form.current_role}
                    onChange={(e) => { setForm({ ...form, current_role: e.target.value }); setFieldErrors((fe) => ({ ...fe, current_role: "" })); }}
                    className={`w-full bg-surface border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent/60 transition-colors ${fieldErrors.current_role ? "border-red-400" : "border-border"}`}
                  />
                  {fieldErrors.current_role && <p className="text-xs text-red-400 mt-1 px-1">{fieldErrors.current_role}</p>}
                </div>
                <div>
                  <input
                    placeholder="Meta de carreira (ex: Cloud Architect)"
                    value={form.target_role}
                    onChange={(e) => { setForm({ ...form, target_role: e.target.value }); setFieldErrors((fe) => ({ ...fe, target_role: "" })); }}
                    className={`w-full bg-surface border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent/60 transition-colors ${fieldErrors.target_role ? "border-red-400" : "border-border"}`}
                  />
                  {fieldErrors.target_role && <p className="text-xs text-red-400 mt-1 px-1">{fieldErrors.target_role}</p>}
                </div>
                <input
                  type="number"
                  min="0"
                  max="40"
                  placeholder="Anos de experiência"
                  value={form.experience_years}
                  onChange={(e) => setForm({ ...form, experience_years: e.target.value })}
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent/60 transition-colors"
                />
                <div>
                  <p className="text-xs text-text-muted mb-2">Skills que você já conhece:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {SKILLS.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => toggleSkill(s)}
                        className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                          selectedSkills.includes(s)
                            ? "bg-accent text-surface"
                            : "bg-surface border border-border text-text-muted hover:text-text-primary"
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {error && (
              <p className="text-red-400 text-xs px-1">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-accent text-surface font-semibold rounded-lg hover:bg-accent-dim transition-colors disabled:opacity-50 mt-1"
            >
              {loading
                ? "Aguarde..."
                : mode === "login"
                ? "Entrar"
                : "Criar conta e gerar roadmap"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
