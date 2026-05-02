import { randomBetween } from "../core/math.js";

export function createPlayer(config) {
  return {
    x: config.worldWidth / 2,
    y: config.worldHeight / 2,
    vx: 0,
    vy: 0,
    radius: config.playerRadius,
    energy: 100,
    shieldUntil: 0,
    boostUntil: 0,
    magnetUntil: 0,
  };
}

export function createObstacles(config) {
  return Array.from({ length: config.obstacleCount }, () => ({
    x: randomBetween(80, config.worldWidth - 80),
    y: randomBetween(80, config.worldHeight - 80),
    radius: randomBetween(18, 46),
    spin: randomBetween(0, Math.PI),
  }));
}

export function createEnergy(config) {
  return Array.from({ length: config.energyCount }, () => createEnergyOrb(config));
}

export function createEnergyOrb(config) {
  return {
    x: randomBetween(60, config.worldWidth - 60),
    y: randomBetween(60, config.worldHeight - 60),
    radius: randomBetween(5, 9),
    pulse: randomBetween(0, Math.PI * 2),
  };
}

export function createPowerUps(config) {
  return Array.from({ length: 7 }, () => createPowerUp(config));
}

export function createPowerUp(config) {
  const types = ["shield", "boost", "magnet"];
  return {
    x: randomBetween(90, config.worldWidth - 90),
    y: randomBetween(90, config.worldHeight - 90),
    radius: 12,
    type: types[Math.floor(Math.random() * types.length)],
    pulse: randomBetween(0, Math.PI * 2),
  };
}
