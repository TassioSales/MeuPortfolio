import { getConfig, getLeaderboard, submitScore } from "./api/client.js";
import { Input } from "./core/input.js";
import { Sound } from "./core/sound.js";
import { Game } from "./game/game.js";

const canvas = document.querySelector("#game");
const menu = document.querySelector("#menu");
const startButton = document.querySelector("#startButton");
const pilotName = document.querySelector("#pilotName");
const score = document.querySelector("#score");
const energy = document.querySelector("#energy");
const power = document.querySelector("#power");
const best = document.querySelector("#best");
const leaderboard = document.querySelector("#leaderboard");

let game;
const sound = new Sound();

function setBest(value) {
  const current = Number(localStorage.getItem("neon-drift-best") || 0);
  const next = Math.max(current, value);
  localStorage.setItem("neon-drift-best", String(next));
  best.textContent = String(next);
}

async function renderLeaderboard() {
  const entries = await getLeaderboard();
  leaderboard.innerHTML = entries.length
    ? entries.map((entry) => `<li>${entry.name} - ${entry.score}</li>`).join("")
    : "<li>Nenhuma run enviada ainda</li>";
}

async function boot() {
  const config = await getConfig();
  const input = new Input();

  best.textContent = localStorage.getItem("neon-drift-best") || "0";
  await renderLeaderboard();

  game = new Game({
    canvas,
    input,
    config,
    onUpdate: (state) => {
      score.textContent = String(state.score);
      energy.textContent = String(Math.ceil(state.player.energy));
      power.textContent = activePowerLabel(state);
    },
    onGameOver: async (result) => {
      setBest(result.score);
      menu.classList.remove("hidden");
      startButton.textContent = "Restart Run";
      await submitScore(result);
      await renderLeaderboard();
    },
    onSound: (event) => {
      sound[event]?.();
    },
  });
}

startButton.addEventListener("click", () => {
  sound.start();
  menu.classList.add("hidden");
  score.textContent = "0";
  energy.textContent = "100";
  power.textContent = "None";
  game.start(pilotName.value);
});

function activePowerLabel(state) {
  const active = [
    ["Shield", state.player.shieldUntil],
    ["Boost", state.player.boostUntil],
    ["Magnet", state.player.magnetUntil],
  ].find(([, until]) => state.elapsed < until);

  return active ? active[0] : "None";
}

boot().catch((error) => {
  console.error(error);
  startButton.textContent = "Backend offline";
  startButton.disabled = true;
});
