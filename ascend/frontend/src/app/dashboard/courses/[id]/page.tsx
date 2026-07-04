"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronLeft, BookOpen, Clock, CheckCircle2, Circle,
  ChevronRight, ChevronDown, Play, Zap, Code2, Lightbulb,
  Trophy, Lock,
} from "lucide-react";
import { api, type BuiltinCourse, type Lesson, type CourseModule } from "@/lib/api";
import { PageTransition } from "@/components/layout/PageTransition";
import { toast } from "@/lib/toast";

const LANG_LABELS: Record<string, string> = {
  python: "Python", sql: "SQL", bash: "Shell", javascript: "JavaScript",
  typescript: "TypeScript", hcl: "Terraform", yaml: "YAML", dax: "DAX",
  markdown: "Markdown", go: "Go",
};

function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!code) return null;
  return (
    <div className="rounded-xl border border-border overflow-hidden mt-3">
      <div className="flex items-center justify-between px-4 py-2 bg-surface-high border-b border-border">
        <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
          {LANG_LABELS[lang] ?? lang}
        </span>
        <button
          onClick={copy}
          className="text-[11px] text-text-dim hover:text-text-muted transition-colors"
        >
          {copied ? "Copiado!" : "Copiar"}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-xs leading-relaxed text-text-secondary bg-surface font-mono">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function LessonViewer({
  lesson,
  isCompleted,
  onComplete,
}: {
  lesson: Lesson;
  isCompleted: boolean;
  onComplete: () => void;
}) {
  return (
    <motion.div
      key={lesson.id}
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-6 max-w-3xl"
    >
      {/* Lesson header */}
      <div>
        <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
          <Clock size={12} />
          {lesson.duration_min} min
          {isCompleted && (
            <span className="flex items-center gap-1 text-emerald-400 ml-2">
              <CheckCircle2 size={12} />
              Concluída
            </span>
          )}
        </div>
        <h2 className="text-xl font-bold text-text-primary">{lesson.title}</h2>
        <p className="text-sm text-text-muted mt-2 leading-relaxed">{lesson.intro}</p>
      </div>

      {/* Sections */}
      {lesson.sections.map((section, idx) => (
        <div key={idx} className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center text-[10px] font-bold text-accent">
              {idx + 1}
            </div>
            <h3 className="text-sm font-semibold text-text-primary">{section.heading}</h3>
          </div>
          <p className="text-sm text-text-muted leading-relaxed pl-7">{section.body}</p>
          {section.code && (
            <div className="pl-7">
              <CodeBlock code={section.code} lang={section.lang} />
            </div>
          )}
        </div>
      ))}

      {/* Exercise */}
      {lesson.exercise && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Code2 size={14} className="text-amber-400" />
            <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Exercício</span>
          </div>
          <p className="text-sm text-text-secondary leading-relaxed">{lesson.exercise}</p>
        </div>
      )}

      {/* Takeaway */}
      {lesson.takeaway && (
        <div className="rounded-xl border border-accent/20 bg-accent/5 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb size={14} className="text-accent" />
            <span className="text-xs font-semibold text-accent uppercase tracking-wider">Takeaway</span>
          </div>
          <p className="text-sm text-text-secondary leading-relaxed">{lesson.takeaway}</p>
        </div>
      )}

      {/* Complete button */}
      <button
        onClick={onComplete}
        disabled={isCompleted}
        className={`flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-all ${
          isCompleted
            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 cursor-default"
            : "bg-accent text-bg-base hover:bg-accent/90 active:scale-[0.98]"
        }`}
      >
        {isCompleted ? (
          <>
            <CheckCircle2 size={16} />
            Aula concluída
          </>
        ) : (
          <>
            <Zap size={16} />
            Marcar como concluída
          </>
        )}
      </button>
    </motion.div>
  );
}

function ModuleSidebar({
  modules,
  completedLessons,
  activeLessonId,
  onSelect,
}: {
  modules: CourseModule[];
  completedLessons: Set<string>;
  activeLessonId: string;
  onSelect: (lesson: Lesson, moduleIdx: number, lessonIdx: number) => void;
}) {
  const [openModules, setOpenModules] = useState<Set<number>>(new Set([0]));

  const toggle = (idx: number) =>
    setOpenModules((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });

  return (
    <nav className="flex flex-col gap-1">
      {modules.map((mod, mIdx) => {
        const isOpen = openModules.has(mIdx);
        const completed = mod.lessons.filter((l) => completedLessons.has(l.id)).length;
        return (
          <div key={mod.id} className="rounded-xl border border-border overflow-hidden">
            <button
              onClick={() => toggle(mIdx)}
              className="w-full flex items-center justify-between px-4 py-3 bg-surface-high hover:bg-surface-card transition-colors"
            >
              <div className="text-left">
                <span className="text-xs font-semibold text-text-primary">{mod.title}</span>
                <p className="text-[11px] text-text-dim mt-0.5">
                  {completed}/{mod.lessons.length} aulas
                </p>
              </div>
              <ChevronDown
                size={14}
                className={`text-text-dim transition-transform ${isOpen ? "rotate-180" : ""}`}
              />
            </button>

            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: "auto" }}
                  exit={{ height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  {mod.lessons.map((lesson, lIdx) => {
                    const done = completedLessons.has(lesson.id);
                    const active = lesson.id === activeLessonId;
                    return (
                      <button
                        key={lesson.id}
                        onClick={() => onSelect(lesson, mIdx, lIdx)}
                        className={`w-full flex items-center gap-3 px-4 py-2.5 text-left border-t border-border/50 transition-colors ${
                          active
                            ? "bg-accent/10 text-accent"
                            : "hover:bg-surface-card text-text-muted"
                        }`}
                      >
                        {done ? (
                          <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
                        ) : (
                          <Circle size={13} className="shrink-0 opacity-40" />
                        )}
                        <span className="text-xs leading-snug">{lesson.title}</span>
                        <span className="ml-auto text-[10px] text-text-dim shrink-0">
                          {lesson.duration_min}m
                        </span>
                      </button>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </nav>
  );
}

export default function CourseViewerPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [course, setCourse] = useState<BuiltinCourse | null>(null);
  const [completedLessons, setCompletedLessons] = useState<Set<string>>(new Set());
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
  const [activePath, setActivePath] = useState<[number, number]>([0, 0]);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.trilha.get(id);
      setCourse(data);
      setCompletedLessons(new Set(data.completed_lessons));
      const first = data.modules[0]?.lessons[0];
      if (first) {
        setActiveLesson(first);
        setActivePath([0, 0]);
      }
    } catch {
      router.push("/dashboard/courses");
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  useEffect(() => { load(); }, [load]);

  const handleEnroll = async () => {
    if (!course) return;
    setEnrolling(true);
    try {
      await api.trilha.enroll(course.id);
      setCourse((c) => c ? { ...c, enrolled: true } : c);
      toast.success("Matrícula realizada!");
    } catch {
      toast.error("Erro ao matricular");
    } finally {
      setEnrolling(false);
    }
  };

  const handleCompleteLesson = async () => {
    if (!course || !activeLesson) return;
    try {
      const res = await api.trilha.completeLesson(course.id, activeLesson.id);
      setCompletedLessons(new Set(res.completed_lessons));
      setCourse((c) => c ? { ...c, progress_pct: res.progress_pct } : c);
      toast.success("Aula concluída!");
      goNext();
    } catch {
      toast.error("Erro ao salvar progresso");
    }
  };

  const goNext = () => {
    if (!course) return;
    const [mIdx, lIdx] = activePath;
    const mod = course.modules[mIdx];
    if (lIdx < mod.lessons.length - 1) {
      const next = mod.lessons[lIdx + 1];
      setActiveLesson(next);
      setActivePath([mIdx, lIdx + 1]);
    } else if (mIdx < course.modules.length - 1) {
      const next = course.modules[mIdx + 1].lessons[0];
      setActiveLesson(next);
      setActivePath([mIdx + 1, 0]);
    }
  };

  const goPrev = () => {
    if (!course) return;
    const [mIdx, lIdx] = activePath;
    if (lIdx > 0) {
      const prev = course.modules[mIdx].lessons[lIdx - 1];
      setActiveLesson(prev);
      setActivePath([mIdx, lIdx - 1]);
    } else if (mIdx > 0) {
      const prevMod = course.modules[mIdx - 1];
      const prev = prevMod.lessons[prevMod.lessons.length - 1];
      setActiveLesson(prev);
      setActivePath([mIdx - 1, prevMod.lessons.length - 1]);
    }
  };

  const totalLessons = course?.modules.reduce((s, m) => s + m.lessons.length, 0) ?? 0;
  const flatIdx = course
    ? course.modules.slice(0, activePath[0]).reduce((s, m) => s + m.lessons.length, 0) + activePath[1]
    : 0;
  const hasPrev = flatIdx > 0;
  const hasNext = flatIdx < totalLessons - 1;

  if (loading) {
    return (
      <PageTransition>
        <div className="flex items-center justify-center h-screen text-text-muted text-sm">
          Carregando curso...
        </div>
      </PageTransition>
    );
  }

  if (!course) return null;

  return (
    <PageTransition>
      <div className="flex flex-col h-screen overflow-hidden">
        {/* Top bar */}
        <div className="shrink-0 px-6 py-3 border-b border-border bg-surface/80 backdrop-blur-sm flex items-center gap-4">
          <button
            onClick={() => router.push("/dashboard/courses")}
            className="flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors"
          >
            <ChevronLeft size={16} />
            Cursos
          </button>

          <div className="w-px h-4 bg-border" />

          <div className="flex-1 min-w-0">
            <span className="text-sm font-semibold text-text-primary truncate">{course.title}</span>
          </div>

          {/* Progress */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="hidden sm:flex items-center gap-2">
              <div className="w-32 h-1.5 bg-surface-high rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-500"
                  style={{ width: `${course.progress_pct}%` }}
                />
              </div>
              <span className="text-xs text-text-muted">{course.progress_pct}%</span>
            </div>

            {!course.enrolled && (
              <button
                onClick={handleEnroll}
                disabled={enrolling}
                className="flex items-center gap-1.5 text-xs font-semibold bg-accent text-bg-base px-3 py-1.5 rounded-lg hover:bg-accent/90 transition-all disabled:opacity-60"
              >
                <Play size={11} />
                {enrolling ? "Matriculando..." : "Matricular-se"}
              </button>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <aside className="w-72 shrink-0 border-r border-border overflow-y-auto p-4 bg-surface/50">
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-1">
                <Trophy size={13} className="text-accent" />
                <span className="text-xs font-semibold text-text-muted">
                  {completedLessons.size} / {totalLessons} aulas
                </span>
              </div>
              <div className="w-full h-1 bg-surface-high rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-500"
                  style={{ width: `${course.progress_pct}%` }}
                />
              </div>
            </div>

            <ModuleSidebar
              modules={course.modules}
              completedLessons={completedLessons}
              activeLessonId={activeLesson?.id ?? ""}
              onSelect={(lesson, mIdx, lIdx) => {
                setActiveLesson(lesson);
                setActivePath([mIdx, lIdx]);
              }}
            />
          </aside>

          {/* Lesson content */}
          <main className="flex-1 overflow-y-auto px-8 py-8">
            {!course.enrolled && (
              <div className="mb-6 flex items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
                <Lock size={14} className="text-amber-400 shrink-0" />
                <p className="text-sm text-amber-300">
                  Matricule-se para rastrear seu progresso e marcar aulas como concluídas.
                </p>
                <button
                  onClick={handleEnroll}
                  disabled={enrolling}
                  className="ml-auto text-xs font-semibold text-amber-400 hover:text-amber-300 transition-colors shrink-0"
                >
                  {enrolling ? "..." : "Matricular"}
                </button>
              </div>
            )}

            {activeLesson ? (
              <LessonViewer
                lesson={activeLesson}
                isCompleted={completedLessons.has(activeLesson.id)}
                onComplete={handleCompleteLesson}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-text-muted">
                <BookOpen size={32} className="mb-3 opacity-30" />
                <p className="text-sm">Selecione uma aula no painel lateral</p>
              </div>
            )}

            {/* Prev / Next navigation */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-border max-w-3xl">
              <button
                onClick={goPrev}
                disabled={!hasPrev}
                className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary transition-colors disabled:opacity-30 disabled:cursor-default"
              >
                <ChevronLeft size={16} />
                Anterior
              </button>
              <span className="text-xs text-text-dim">
                Aula {flatIdx + 1} de {totalLessons}
              </span>
              <button
                onClick={goNext}
                disabled={!hasNext}
                className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary transition-colors disabled:opacity-30 disabled:cursor-default"
              >
                Próxima
                <ChevronRight size={16} />
              </button>
            </div>
          </main>
        </div>
      </div>
    </PageTransition>
  );
}
