"use client";
import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen, ExternalLink, Star, Clock, Tag, Zap,
  ChevronDown, Filter, Sparkles
} from "lucide-react";
import { api, type Course } from "@/lib/api";
import { PageTransition } from "@/components/layout/PageTransition";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/Skeleton";

const LEVEL_COLORS: Record<string, string> = {
  "Iniciante":     "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  "Intermediário": "bg-amber-500/10 text-amber-400 border-amber-500/20",
  "Avançado":      "bg-red-500/10 text-red-400 border-red-500/20",
};

function CourseCard({ course, index }: { course: Course; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.35 }}
      className="group relative bg-surface-card border border-border hover:border-border-bright rounded-2xl p-5 flex flex-col gap-3 shadow-card hover:shadow-card-hover transition-all"
    >
      {/* Free badge */}
      {course.is_free && (
        <span className="absolute top-3.5 right-3.5 text-[10px] font-bold uppercase tracking-wider bg-accent/10 text-accent border border-accent/20 px-2 py-0.5 rounded-full">
          Grátis
        </span>
      )}

      {/* Header */}
      <div className="pr-12">
        <h3 className="text-sm font-semibold text-text-primary leading-snug group-hover:text-accent transition-colors">
          {course.title}
        </h3>
        <p className="text-xs text-text-muted mt-0.5">{course.platform}</p>
      </div>

      {/* Description */}
      <p className="text-xs text-text-muted leading-relaxed line-clamp-2">{course.description}</p>

      {/* Meta row */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-[10px] font-semibold border px-2 py-0.5 rounded-full ${LEVEL_COLORS[course.level] ?? "bg-surface-high text-text-muted border-border"}`}>
          {course.level}
        </span>
        <span className="flex items-center gap-1 text-[11px] text-text-muted">
          <Clock size={10} />
          {course.duration}
        </span>
        <span className="flex items-center gap-1 text-[11px] text-amber-400">
          <Star size={10} fill="currentColor" />
          {course.rating.toFixed(1)}
        </span>
      </div>

      {/* Skills */}
      {course.skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {course.skills.slice(0, 4).map((s) => (
            <span key={s} className="text-[10px] bg-surface-high text-text-muted px-2 py-0.5 rounded-md border border-border">
              {s}
            </span>
          ))}
          {course.skills.length > 4 && (
            <span className="text-[10px] text-text-dim">+{course.skills.length - 4}</span>
          )}
        </div>
      )}

      {/* CTA */}
      <a
        href={course.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-auto flex items-center gap-2 text-xs font-semibold text-accent hover:text-accent/80 transition-colors"
      >
        Acessar curso
        <ExternalLink size={12} />
      </a>
    </motion.div>
  );
}

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [recommended, setRecommended] = useState<Course[]>([]);
  const [milestoneTitle, setMilestoneTitle] = useState<string>("");
  const [categories, setCategories] = useState<string[]>([]);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [tab, setTab] = useState<"recommended" | "all">("recommended");
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [recResult, catResult] = await Promise.all([
        api.courses.recommended(),
        api.courses.categories(),
      ]);
      setRecommended(recResult.courses);
      setMilestoneTitle(recResult.milestone_title ?? "");
      setCategories(catResult.categories);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCatalog = useCallback(async (cat?: string) => {
    setLoading(true);
    try {
      const res = await api.courses.list(cat);
      setCourses(res.courses);
    } catch {
      //
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    loadCatalog();
  }, [loadData, loadCatalog]);

  const handleCategory = (cat: string | null) => {
    setActiveCategory(cat);
    loadCatalog(cat ?? undefined);
  };

  const displayed = tab === "recommended" ? recommended : courses;

  return (
    <PageTransition>
      <div className="flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <div className="shrink-0 px-8 pt-8 pb-4 border-b border-border bg-surface/80 backdrop-blur-sm">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2.5 mb-1">
                <div className="w-8 h-8 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center">
                  <BookOpen size={15} className="text-accent" />
                </div>
                <h1 className="text-xl font-bold text-text-primary">Cursos</h1>
              </div>
              {milestoneTitle && tab === "recommended" && (
                <p className="text-sm text-text-muted flex items-center gap-1.5">
                  <Sparkles size={12} className="text-accent" />
                  Recomendados para o milestone:&nbsp;
                  <span className="text-text-primary font-medium">{milestoneTitle}</span>
                </p>
              )}
              {!milestoneTitle && tab === "recommended" && (
                <p className="text-sm text-text-muted">Cursos selecionados para o seu perfil</p>
              )}
              {tab === "all" && (
                <p className="text-sm text-text-muted">
                  {courses.length} cursos disponíveis
                  {activeCategory ? ` em ${activeCategory}` : ""}
                </p>
              )}
            </div>

            {tab === "all" && (
              <button
                onClick={() => setShowFilters(f => !f)}
                className="flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary border border-border hover:border-border-bright px-3 py-1.5 rounded-lg transition-all"
              >
                <Filter size={13} />
                Filtrar
                <ChevronDown size={12} className={`transition-transform ${showFilters ? "rotate-180" : ""}`} />
              </button>
            )}
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-4">
            {[
              { key: "recommended" as const, label: "Recomendados", icon: Zap },
              { key: "all" as const, label: "Catálogo completo", icon: BookOpen },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  tab === key
                    ? "bg-accent/10 text-accent border border-accent/20"
                    : "text-text-muted hover:text-text-primary hover:bg-surface-high"
                }`}
              >
                <Icon size={13} />
                {label}
              </button>
            ))}
          </div>

          {/* Category filters */}
          <AnimatePresence>
            {tab === "all" && showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="flex flex-wrap gap-2 pt-3">
                  <button
                    onClick={() => handleCategory(null)}
                    className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition-all ${
                      !activeCategory
                        ? "bg-accent/10 text-accent border-accent/20 font-semibold"
                        : "text-text-muted border-border hover:border-border-bright"
                    }`}
                  >
                    <Tag size={10} />
                    Todos
                  </button>
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      onClick={() => handleCategory(cat)}
                      className={`text-xs px-3 py-1.5 rounded-full border transition-all ${
                        activeCategory === cat
                          ? "bg-accent/10 text-accent border-accent/20 font-semibold"
                          : "text-text-muted border-border hover:border-border-bright"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : displayed.length === 0 ? (
            <EmptyState
              icon={<BookOpen size={28} className="text-text-dim" />}
              title="Nenhum curso encontrado"
              description="Tente outra categoria ou acesse o catálogo completo."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {displayed.map((course, i) => (
                <CourseCard key={course.id} course={course} index={i} />
              ))}
            </div>
          )}
        </div>
      </div>
    </PageTransition>
  );
}
