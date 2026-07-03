const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("ascend_token");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("ascend_token");
      window.location.href = "/login";
    }
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erro na requisição");
  }
  return res.json();
}

export const api = {
  auth: {
    register: (data: object) =>
      request<{ access_token: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    login: (email: string, password: string) =>
      request<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    me: () => request<UserProfile>("/auth/me"),
  },
  career: {
    getRoadmap: () => request<CareerPathResponse>("/career/roadmap"),
    getProgress: () => request<MilestoneProgress[]>("/career/progress"),
    updateMilestone: (index: number, status: string, minutes = 0) =>
      request("/career/milestones/" + index, {
        method: "PATCH",
        body: JSON.stringify({ status, time_spent_minutes: minutes }),
      }),
    regenerate: () =>
      request("/career/roadmap/generate", { method: "POST" }),
  },
  analytics: {
    getSummary: () => request<AnalyticsSummary>("/analytics/summary"),
  },
  mentorship: {
    getMentors: () => request<Mentor[]>("/mentorship/mentors"),
    getSlots: () => request<Slot[]>("/mentorship/slots"),
    book: (mentor_id: number, scheduled_at: string, topic: string) =>
      request("/mentorship/book", {
        method: "POST",
        body: JSON.stringify({ mentor_id, scheduled_at, topic }),
      }),
    mySessions: (skip = 0, limit = 20) =>
      request<MentorSession[]>(`/mentorship/my-sessions?skip=${skip}&limit=${limit}`),
  },
  coach: {
    history: (skip = 0, limit = 50) =>
      request<ChatHistoryItem[]>(`/coach/chat/history?skip=${skip}&limit=${limit}`),
  },
  courses: {
    list: (category?: string) =>
      request<{ courses: Course[] }>(`/courses${category ? `?category=${encodeURIComponent(category)}` : ""}`),
    recommended: () =>
      request<{ courses: Course[]; source: string; milestone_title?: string; milestone_index?: number }>("/courses/recommended"),
    categories: () =>
      request<{ categories: string[] }>("/courses/categories"),
  },
};

export async function streamChat(
  messages: { role: string; content: string }[],
  onToken: (t: string) => void
): Promise<void> {
  const token = getToken();
  const res = await fetch(`${BASE}/coach/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ messages }),
  });

  if (res.status === 401) {
    localStorage.removeItem("ascend_token");
    window.location.href = "/login";
    return;
  }

  const reader = res.body?.getReader();
  const decoder = new TextDecoder();
  if (!reader) return;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value);
    for (const line of chunk.split("\n")) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") return;
        onToken(data);
      }
    }
  }
}

export async function streamSimulation(
  endpoint: "start" | "respond",
  params: {
    scenario?: string;
    session_id?: string;
    user_message?: string;
    history?: { role: string; content: string }[];
  },
  onToken: (t: string) => void,
  onSessionId?: (id: string) => void
): Promise<void> {
  const token = getToken();

  let url: string;
  let init: RequestInit;

  if (endpoint === "start") {
    url = `${BASE}/simulation/start?scenario=${params.scenario ?? "client_requirements"}`;
    init = {
      method: "POST",
      headers: { Authorization: `Bearer ${token ?? ""}` },
    };
  } else {
    url = `${BASE}/simulation/respond`;
    init = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token ?? ""}`,
      },
      body: JSON.stringify({
        session_id: params.session_id,
        user_message: params.user_message,
        scenario: params.scenario ?? "client_requirements",
        history: params.history ?? [],
      }),
    };
  }

  const res = await fetch(url, init);
  if (res.status === 401) {
    localStorage.removeItem("ascend_token");
    window.location.href = "/login";
    return;
  }

  const reader = res.body?.getReader();
  const decoder = new TextDecoder();
  if (!reader) return;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    for (const line of decoder.decode(value).split("\n")) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6);
      if (data === "[DONE]") return;
      if (data.startsWith("[SESSION:") && onSessionId) {
        onSessionId(data.slice(9, -1));
        continue;
      }
      onToken(data);
    }
  }
}

// Types
export interface UserProfile {
  id: number; email: string; name: string;
  current_role: string; target_role: string;
  experience_years: number; known_skills: string[];
}
export interface Milestone {
  index: number; title: string; description: string;
  skills: string[]; estimated_hours: number; resources: string[];
}
export interface CareerPathResponse {
  milestones: Milestone[]; generated_at: string;
  progress_pct: number; current_milestone_index: number;
}
export interface MilestoneProgress {
  milestone_index: number; status: string;
  time_spent_minutes: number; started_at: string | null; completed_at: string | null;
}
export interface AnalyticsSummary {
  total_milestones: number; completed: number; in_progress: number;
  not_started: number; progress_pct: number; total_hours_studied: number;
  avg_hours_per_milestone: number; estimated_hours_remaining: number;
  estimated_completion_date: string | null; current_role: string; target_role: string;
}
export interface Mentor {
  id: number; name: string; role: string; specialty: string; avatar: string;
  bio: string; rating: number; sessions_done: number;
}
export interface Slot { datetime: string; available: boolean; }
export interface MentorSession {
  id: number; mentor_name: string; mentor_role: string;
  scheduled_at: string; topic: string; status: string;
}
export interface ChatHistoryItem {
  id: number; role: string; content: string; created_at: string;
}
export interface Course {
  id: number; title: string; platform: string; url: string;
  duration: string; level: string; skills: string[];
  is_free: boolean; rating: number; description: string; category: string;
}
