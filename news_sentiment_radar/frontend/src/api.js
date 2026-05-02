export async function getSummary() {
  const response = await fetch("/api/summary");
  return response.json();
}

export async function getArticles() {
  const response = await fetch("/api/articles");
  return response.json();
}

export async function refreshNews() {
  const response = await fetch("/api/refresh", { method: "POST" });
  return response.json();
}
