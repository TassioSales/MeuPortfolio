export class Input {
  constructor() {
    this.keys = new Set();
    this.pointer = { x: 0, y: 0, active: false };

    window.addEventListener("keydown", (event) => this.keys.add(event.key.toLowerCase()));
    window.addEventListener("keyup", (event) => this.keys.delete(event.key.toLowerCase()));
    window.addEventListener("pointermove", (event) => {
      this.pointer.x = event.clientX;
      this.pointer.y = event.clientY;
      this.pointer.active = true;
    });
  }

  axis() {
    const x = Number(this.keys.has("d") || this.keys.has("arrowright")) - Number(this.keys.has("a") || this.keys.has("arrowleft"));
    const y = Number(this.keys.has("s") || this.keys.has("arrowdown")) - Number(this.keys.has("w") || this.keys.has("arrowup"));
    return { x, y };
  }
}
