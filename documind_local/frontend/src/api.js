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

async function request(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Request failed: ${path}`);
  }
  return response.json();
}
