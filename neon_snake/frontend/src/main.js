import { getConfig, getLeaderboard, submitScore } from "./api.js";
import { Sound } from "./sound.js";

const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const scoreEl = document.querySelector("#score");
const lengthEl = document.querySelector("#length");
const bestEl = document.querySelector("#best");
const playerName = document.querySelector("#playerName");
const startButton = document.querySelector("#startButton");
const leaderboardEl = document.querySelector("#leaderboard");

let config;
let snake;
let food;
let direction;
let nextDirection;
let score;
let running = false;
let timer;
const sound = new Sound();

const colors = {
  head: "#22d3ee",
  body: "#a3e635",
  food: "#f472b6",
  grid: "rgba(34, 211, 238, 0.08)",
};

function reset() {
  const mid = Math.floor(config.gridSize / 2);
  snake = [
    { x: mid, y: mid },
    { x: mid - 1, y: mid },
    { x: mid - 2, y: mid },
  ];
  direction = { x: 1, y: 0 };
  nextDirection = direction;
  score = 0;
  food = placeFood();
  syncHud();
  draw();
}

function placeFood() {
  let candidate;
  do {
    candidate = {
      x: Math.floor(Math.random() * config.gridSize),
      y: Math.floor(Math.random() * config.gridSize),
    };
  } while (snake.some((part) => part.x === candidate.x && part.y === candidate.y));
  return candidate;
}

function tick() {
  direction = nextDirection;
  const head = snake[0];
  const next = { x: head.x + direction.x, y: head.y + direction.y };

  if (
    next.x < 0 ||
    next.y < 0 ||
    next.x >= config.gridSize ||
    next.y >= config.gridSize ||
    snake.some((part) => part.x === next.x && part.y === next.y)
  ) {
    gameOver();
    return;
  }

  snake.unshift(next);
  if (next.x === food.x && next.y === food.y) {
    score += config.foodScore + snake.length * 6;
    food = placeFood();
    sound.eat();
    restartTimer();
  } else {
    snake.pop();
  }

  syncHud();
  draw();
}

function draw() {
  const size = canvas.width / config.gridSize;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#05070b";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = colors.grid;
  for (let i = 0; i <= config.gridSize; i += 1) {
    const pos = i * size;
    ctx.beginPath();
    ctx.moveTo(pos, 0);
    ctx.lineTo(pos, canvas.height);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, pos);
    ctx.lineTo(canvas.width, pos);
    ctx.stroke();
  }

  drawCell(food, colors.food, size, 0.35);
  snake.forEach((part, index) => drawCell(part, index === 0 ? colors.head : colors.body, size, 0.18));
}

function drawCell(cell, color, size, insetRatio) {
  const inset = size * insetRatio;
  ctx.shadowBlur = 18;
  ctx.shadowColor = color;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(cell.x * size + inset, cell.y * size + inset, size - inset * 2, size - inset * 2, 7);
  ctx.fill();
  ctx.shadowBlur = 0;
}

function restartTimer() {
  clearInterval(timer);
  const speed = Math.max(config.minSpeed, config.initialSpeed - snake.length * 3);
  timer = setInterval(tick, speed);
}

async function gameOver() {
  running = false;
  clearInterval(timer);
  sound.crash();
  startButton.textContent = "Restart";
  const best = Math.max(Number(localStorage.getItem("neon-snake-best") || 0), score);
  localStorage.setItem("neon-snake-best", String(best));
  bestEl.textContent = String(best);
  await submitScore({ name: playerName.value, score, length: snake.length });
  await renderLeaderboard();
}

function syncHud() {
  scoreEl.textContent = String(score);
  lengthEl.textContent = String(snake.length);
}

function setDirection(x, y) {
  if (direction.x + x === 0 && direction.y + y === 0) {
    return;
  }
  nextDirection = { x, y };
  if (running) {
    sound.turn();
  }
}

async function renderLeaderboard() {
  const entries = await getLeaderboard();
  leaderboardEl.innerHTML = entries.length
    ? entries.map((entry) => `<li>${entry.name} - ${entry.score}</li>`).join("")
    : "<li>Nenhum score ainda</li>";
}

window.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if (key === "arrowup" || key === "w") setDirection(0, -1);
  if (key === "arrowdown" || key === "s") setDirection(0, 1);
  if (key === "arrowleft" || key === "a") setDirection(-1, 0);
  if (key === "arrowright" || key === "d") setDirection(1, 0);
});

startButton.addEventListener("click", () => {
  sound.start();
  reset();
  running = true;
  startButton.textContent = "Running";
  restartTimer();
});

async function boot() {
  config = await getConfig();
  bestEl.textContent = localStorage.getItem("neon-snake-best") || "0";
  reset();
  await renderLeaderboard();
}

boot();
