export async function getConfig() {
  const response = await fetch("/api/config");
  return response.json();
}

export async function getLeaderboard() {
  const response = await fetch("/api/leaderboard");
  return response.ok ? response.json() : [];
}

export async function submitScore(score) {
  const response = await fetch("/api/scores", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(score),
  });
  return response.ok;
}
