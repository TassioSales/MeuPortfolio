"use client";
import { useEffect, useState } from "react";
import { Calendar, Clock, User, Star } from "lucide-react";
import { api, type Mentor, type Slot, type MentorSession } from "@/lib/api";
import { toast } from "@/lib/toast";
import { PageTransition } from "@/components/layout/PageTransition";
import { EmptyState } from "@/components/ui/EmptyState";

export default function MentorshipPage() {
  const [mentors, setMentors] = useState<Mentor[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [mySessions, setMySessions] = useState<MentorSession[]>([]);
  const [selectedMentor, setSelectedMentor] = useState<number | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [topic, setTopic] = useState("");
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    Promise.all([
      api.mentorship.getMentors().then(setMentors),
      api.mentorship.getSlots().then(setSlots),
      api.mentorship.mySessions().then(setMySessions),
    ]).catch(() => toast.error("Erro ao carregar dados de mentoria."));
  }, []);

  async function book() {
    if (!selectedMentor || !selectedSlot || !topic) return;
    setBooking(true);
    try {
      await api.mentorship.book(selectedMentor, selectedSlot, topic);
      toast.success("Sessão agendada com sucesso!");
      const updated = await api.mentorship.mySessions();
      setMySessions(updated);
      setSelectedMentor(null);
      setSelectedSlot(null);
      setTopic("");
    } catch (e: any) {
      toast.error(e.message ?? "Erro ao agendar sessão.");
    } finally {
      setBooking(false);
    }
  }

  return (
    <PageTransition>
      <div className="p-6 max-w-3xl">
        <h1 className="text-xl font-bold text-text-primary mb-1">Mentorship</h1>
        <p className="text-text-muted text-sm mb-6">Agende sessões 1:1 com especialistas</p>

        <div className="grid grid-cols-2 gap-3 mb-6">
          {mentors.map((m) => (
            <button key={m.id} onClick={() => setSelectedMentor(m.id === selectedMentor ? null : m.id)}
              aria-label={`Selecionar mentor ${m.name}`}
              className={`p-4 rounded-xl border text-left transition-all ${
                selectedMentor === m.id ? "border-accent bg-accent/5" : "border-border bg-surface-raised hover:border-accent/40"
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center text-accent text-xs font-bold">
                  {m.avatar}
                </div>
                <div>
                  <p className="text-sm font-semibold text-text-primary">{m.name}</p>
                  <p className="text-xs text-text-muted">{m.specialty}</p>
                </div>
                <div className="ml-auto flex items-center gap-0.5 text-xs text-yellow-400">
                  <Star size={10} fill="currentColor" />
                  {m.rating}
                </div>
              </div>
              <p className="text-xs text-text-muted">{m.role}</p>
              {m.bio && <p className="text-xs text-text-muted mt-1 line-clamp-2">{m.bio}</p>}
            </button>
          ))}
        </div>

        {selectedMentor && (
          <div className="bg-surface-raised border border-border rounded-xl p-4 mb-6">
            <p className="text-sm font-semibold text-text-primary mb-3">Escolha um horário</p>
            <div className="grid grid-cols-2 gap-2 mb-4">
              {slots.slice(0, 6).map((s) => (
                <button key={s.datetime} onClick={() => setSelectedSlot(s.datetime)}
                  aria-label={`Horário: ${new Date(s.datetime).toLocaleString("pt-BR")}`}
                  className={`px-3 py-2 rounded-lg text-xs transition-all flex items-center gap-1.5 ${
                    selectedSlot === s.datetime
                      ? "bg-accent text-surface font-semibold"
                      : "bg-surface border border-border text-text-muted hover:text-text-primary"
                  }`}
                >
                  <Calendar size={11} />
                  {new Date(s.datetime).toLocaleString("pt-BR", {
                    weekday: "short", day: "2-digit", month: "short",
                    hour: "2-digit", minute: "2-digit",
                  })}
                </button>
              ))}
            </div>
            <input value={topic} onChange={(e) => setTopic(e.target.value)}
              placeholder="Tópico da sessão (ex: revisão do meu roadmap AWS)"
              aria-label="Tópico da sessão"
              className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-accent/60 mb-3"
            />
            <button onClick={book} disabled={!selectedSlot || !topic || booking}
              aria-label="Confirmar agendamento"
              className="px-4 py-2 bg-accent text-surface text-sm font-semibold rounded-lg hover:bg-accent-dim transition-colors disabled:opacity-40"
            >
              {booking ? "Agendando..." : "Agendar sessão"}
            </button>
          </div>
        )}

        <div>
          <p className="text-sm font-semibold text-text-primary mb-3">Minhas sessões</p>
          {mySessions.length === 0 ? (
            <EmptyState
              icon={<User size={20} />}
              title="Nenhuma sessão agendada"
              description="Escolha um mentor acima e agende sua primeira sessão 1:1."
            />
          ) : (
            <div className="space-y-2">
              {mySessions.map((s) => (
                <div key={s.id} className="bg-surface-raised border border-border rounded-xl p-3 flex items-center gap-3">
                  <User size={14} className="text-accent" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">{s.mentor_name}</p>
                    <p className="text-xs text-text-muted">{s.topic}</p>
                  </div>
                  <div className="ml-auto text-right">
                    <p className="text-xs text-text-muted flex items-center gap-1 justify-end">
                      <Clock size={10} />
                      {new Date(s.scheduled_at).toLocaleString("pt-BR")}
                    </p>
                    <span className="text-xs text-accent">{s.status}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </PageTransition>
  );
}
