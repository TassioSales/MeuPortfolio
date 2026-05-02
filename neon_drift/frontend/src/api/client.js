const API_BASE = "";

export async function getConfig() {
  const response = await fetch(`${API_BASE}/api/config`);
  if (!response.ok) {
    throw new Error("Failed to load game config");
  }
  return response.json();
}

export async function getLeaderboard() {
  const response = await fetch(`${API_BASE}/api/leaderboard`);
  if (!response.ok) {
    return [];
  }
  return response.json();
}

export async function submitScore(payload) {
  const response = await fetch(`${API_BASE}/api/scores`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to submit score");
  }

  return response.json();
}
