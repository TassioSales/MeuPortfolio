export async function health() {
  return request("/api/health");
}

export async function stats() {
  return request("/api/stats");
}

export async function documents() {
  return request("/api/documents");
}

export async function documentById(id) {
  return request(`/api/documents/${id}`);
}

export async function searchDocuments(query) {
  return request(`/api/search?q=${encodeURIComponent(query)}`);
}

export async function researchTopic(query) {
  return request(`/api/research?q=${encodeURIComponent(query)}`);
}

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/documents", {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    let message = "Upload failed";
    try {
      const error = await response.json();
      message = error.error || message;
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }
  return response.json();
}

export async function deleteDocument(id) {
  return request(`/api/documents/${id}`, { method: "DELETE" });
}

export async function analyzeDocument(id) {
  return request(`/api/documents/${id}/analyze`, { method: "POST" });
}

export async function reviewFlashcard(id, cardId, result) {
  return request(`/api/documents/${id}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cardId, result }),
  });
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `Request failed: ${path}`;
    try {
      const error = await response.json();
      message = error.error || message;
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }
  return response.json();
}
