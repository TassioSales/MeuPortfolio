import type { Entity, GraphData, Note, Relation } from "./types";

const GO_API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  // Handle 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Fetch all notes. */
export async function fetchNotes(): Promise<Note[]> {
  return request<Note[]>(`${GO_API}/notes`);
}

/** Fetch a single note by ID. */
export async function fetchNote(id: number): Promise<Note> {
  return request<Note>(`${GO_API}/notes/${id}`);
}

/** Create a new note with extracted entities and relations. */
export async function createNote(
  title: string,
  content: string,
  entities: Entity[],
  relations: Relation[]
): Promise<Note> {
  return request<Note>(`${GO_API}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, content, entities, relations }),
  });
}

/** Delete a note by ID. */
export async function deleteNote(id: number): Promise<void> {
  return request<void>(`${GO_API}/notes/${id}`, { method: "DELETE" });
}

/** Fetch the full knowledge graph. */
export async function fetchGraph(): Promise<GraphData> {
  return request<GraphData>(`${GO_API}/graph`);
}

/** Call the NLP service via the Next.js proxy. */
export async function extractEntities(
  text: string,
  noteId = "draft"
): Promise<{ entities: Entity[]; relations: Relation[] }> {
  return request(`/api/nlp/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, note_id: noteId }),
  });
}
