import { clamp, distance, normalize } from "../core/math.js";
import { createEnergy, createEnergyOrb, createObstacles, createPlayer, createPowerUp, createPowerUps } from "./entities.js";
import { Renderer } from "./renderer.js";

export class Game {
  constructor({ canvas, input, config, onUpdate, onGameOver, onSound }) {
    this.canvas = canvas;
    this.input = input;
    this.config = config;
    this.onUpdate = onUpdate;
    this.onGameOver = onGameOver;
    this.onSound = onSound;
    this.renderer = new Renderer(canvas);
    this.reset();
  }

  reset() {
    this.state = {
      running: false,
      elapsed: 0,
      score: 0,
      distance: 0,
      player: createPlayer(this.config),
      obstacles: createObstacles(this.config),
      energyOrbs: createEnergy(this.config),
      powerUps: createPowerUps(this.config),
      camera: { x: 0, y: 0 },
    };
  }

  start(name) {
    this.reset();
    this.name = name || "Pilot";
    this.state.running = true;
    this.lastTime = performance.now();
    requestAnimationFrame((time) => this.loop(time));
  }

  loop(time) {
    const delta = Math.min(0.033, (time - this.lastTime) / 1000);
    this.lastTime = time;

    if (this.state.running) {
      this.update(delta);
      requestAnimationFrame((nextTime) => this.loop(nextTime));
    }
    this.renderer.draw(this.state);
  }

  update(delta) {
    const { player } = this.state;
    const axis = this.input.axis();
    const direction = normalize(axis);
    const difficulty = 1 + this.state.elapsed * this.config.difficultyRamp;
    const acceleration = this.config.baseSpeed * 3.2;

    player.vx += direction.x * acceleration * delta;
    player.vy += direction.y * acceleration * delta;
    player.vx *= 0.985;
    player.vy *= 0.985;

    const hasBoost = this.state.elapsed < player.boostUntil;
    const maxSpeed = this.config.baseSpeed * difficulty * (hasBoost ? 1.45 : 1);
    const speed = Math.hypot(player.vx, player.vy);
    if (speed > maxSpeed) {
      player.vx = (player.vx / speed) * maxSpeed;
      player.vy = (player.vy / speed) * maxSpeed;
    }

    player.x = clamp(player.x + player.vx * delta, 0, this.config.worldWidth);
    player.y = clamp(player.y + player.vy * delta, 0, this.config.worldHeight);
    player.energy = clamp(player.energy - delta * (4 + difficulty), 0, 100);

    this.state.elapsed += delta;
    this.state.distance += speed * delta;
    this.state.score = Math.floor(this.state.distance / this.config.scoreMultiplier + this.state.elapsed * 12);
    this.updateCamera();
    this.updateMagnet(delta);
    this.collectEnergy();
    this.collectPowerUps();
    this.checkCollisions();
    this.onUpdate(this.state);

    if (player.energy <= 0) {
      this.finish();
    }
  }

  updateCamera() {
    this.state.camera.x = this.state.player.x - this.renderer.width / 2;
    this.state.camera.y = this.state.player.y - this.renderer.height / 2;
  }

  collectEnergy() {
    const { player } = this.state;
    this.state.energyOrbs = this.state.energyOrbs.map((orb) => {
      if (distance(player, orb) < player.radius + orb.radius) {
        player.energy = clamp(player.energy + 18, 0, 100);
        this.state.score += 75;
        this.onSound("energy");
        return createEnergyOrb(this.config);
      }
      return orb;
    });
  }

  updateMagnet(delta) {
    if (this.state.elapsed >= this.state.player.magnetUntil) {
      return;
    }

    for (const orb of this.state.energyOrbs) {
      const gap = distance(this.state.player, orb);
      if (gap > 0 && gap < 240) {
        orb.x += ((this.state.player.x - orb.x) / gap) * 260 * delta;
        orb.y += ((this.state.player.y - orb.y) / gap) * 260 * delta;
      }
    }
  }

  collectPowerUps() {
    const { player } = this.state;
    this.state.powerUps = this.state.powerUps.map((powerUp) => {
      if (distance(player, powerUp) >= player.radius + powerUp.radius) {
        return powerUp;
      }

      if (powerUp.type === "shield") {
        player.shieldUntil = this.state.elapsed + 6;
      }
      if (powerUp.type === "boost") {
        player.boostUntil = this.state.elapsed + 5;
      }
      if (powerUp.type === "magnet") {
        player.magnetUntil = this.state.elapsed + 7;
      }

      this.state.score += 160;
      this.onSound("power");
      return createPowerUp(this.config);
    });
  }

  checkCollisions() {
    for (const obstacle of this.state.obstacles) {
      if (distance(this.state.player, obstacle) < this.state.player.radius + obstacle.radius * 0.78) {
        if (this.state.elapsed < this.state.player.shieldUntil) {
          this.state.player.shieldUntil = 0;
          this.state.player.vx *= -0.7;
          this.state.player.vy *= -0.7;
          this.state.score += 220;
          this.onSound("shield");
          return;
        }
        this.finish();
        return;
      }
    }
  }

  finish() {
    this.state.running = false;
    this.onSound("gameOver");
    this.onGameOver({
      name: this.name,
      score: this.state.score,
      distance: Math.round(this.state.distance),
      duration: Number(this.state.elapsed.toFixed(2)),
    });
  }
}
