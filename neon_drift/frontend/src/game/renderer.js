export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.resize();
    window.addEventListener("resize", () => this.resize());
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    this.canvas.width = Math.floor(rect.width * ratio);
    this.canvas.height = Math.floor(rect.height * ratio);
    this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.width = rect.width;
    this.height = rect.height;
  }

  draw(state) {
    const { ctx } = this;
    ctx.clearRect(0, 0, this.width, this.height);
    this.drawGrid(state);
    this.drawEnergy(state);
    this.drawPowerUps(state);
    this.drawObstacles(state);
    this.drawPlayer(state);
    this.drawVignette();
  }

  toScreen(state, point) {
    return {
      x: point.x - state.camera.x,
      y: point.y - state.camera.y,
    };
  }

  drawGrid(state) {
    const { ctx } = this;
    const step = 80;
    const startX = -state.camera.x % step;
    const startY = -state.camera.y % step;

    ctx.strokeStyle = "rgba(34, 211, 238, 0.08)";
    ctx.lineWidth = 1;
    for (let x = startX; x < this.width; x += step) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.height);
      ctx.stroke();
    }
    for (let y = startY; y < this.height; y += step) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.width, y);
      ctx.stroke();
    }
  }

  drawPlayer(state) {
    const { ctx } = this;
    const player = this.toScreen(state, state.player);
    const angle = Math.atan2(state.player.vy, state.player.vx);

    ctx.save();
    ctx.translate(player.x, player.y);
    ctx.rotate(angle || 0);
    ctx.shadowBlur = 24;
    ctx.shadowColor = "#22d3ee";
    ctx.fillStyle = "#22d3ee";
    ctx.beginPath();
    ctx.moveTo(22, 0);
    ctx.lineTo(-14, -12);
    ctx.lineTo(-8, 0);
    ctx.lineTo(-14, 12);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    ctx.strokeStyle = "rgba(163, 230, 53, 0.55)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(player.x, player.y, state.player.radius + 8, 0, Math.PI * 2);
    ctx.stroke();

    if (state.elapsed < state.player.shieldUntil) {
      ctx.strokeStyle = "rgba(34, 211, 238, 0.9)";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(player.x, player.y, state.player.radius + 18, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  drawObstacles(state) {
    const { ctx } = this;
    for (const obstacle of state.obstacles) {
      const point = this.toScreen(state, obstacle);
      ctx.save();
      ctx.translate(point.x, point.y);
      ctx.rotate(obstacle.spin + state.elapsed);
      ctx.shadowBlur = 18;
      ctx.shadowColor = "#fb7185";
      ctx.strokeStyle = "#fb7185";
      ctx.lineWidth = 3;
      ctx.strokeRect(-obstacle.radius, -obstacle.radius, obstacle.radius * 2, obstacle.radius * 2);
      ctx.restore();
    }
  }

  drawEnergy(state) {
    const { ctx } = this;
    for (const orb of state.energyOrbs) {
      const point = this.toScreen(state, orb);
      const radius = orb.radius + Math.sin(state.elapsed * 5 + orb.pulse) * 2;
      ctx.shadowBlur = 18;
      ctx.shadowColor = "#a3e635";
      ctx.fillStyle = "#a3e635";
      ctx.beginPath();
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;
  }

  drawPowerUps(state) {
    const palette = {
      shield: "#22d3ee",
      boost: "#facc15",
      magnet: "#c084fc",
    };
    const labels = {
      shield: "S",
      boost: "B",
      magnet: "M",
    };

    const { ctx } = this;
    ctx.font = "900 12px Inter, system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    for (const powerUp of state.powerUps) {
      const point = this.toScreen(state, powerUp);
      const color = palette[powerUp.type];
      const radius = powerUp.radius + Math.sin(state.elapsed * 4 + powerUp.pulse) * 2;
      ctx.shadowBlur = 20;
      ctx.shadowColor = color;
      ctx.fillStyle = "rgba(2, 6, 23, 0.9)";
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.fillStyle = color;
      ctx.fillText(labels[powerUp.type], point.x, point.y + 1);
    }
  }

  drawVignette() {
    const { ctx } = this;
    const gradient = ctx.createRadialGradient(this.width / 2, this.height / 2, 120, this.width / 2, this.height / 2, this.width * 0.7);
    gradient.addColorStop(0, "rgba(7, 8, 13, 0)");
    gradient.addColorStop(1, "rgba(7, 8, 13, 0.78)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, this.width, this.height);
  }
}
