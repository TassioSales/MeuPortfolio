export class Sound {
  constructor() {
    this.context = null;
  }

  unlock() {
    if (!this.context) {
      this.context = new AudioContext();
    }
    if (this.context.state === "suspended") {
      this.context.resume();
    }
  }

  tone(frequency, duration, type = "sine", gain = 0.07, slideTo = null) {
    this.unlock();
    const now = this.context.currentTime;
    const oscillator = this.context.createOscillator();
    const volume = this.context.createGain();

    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, now);
    if (slideTo) {
      oscillator.frequency.exponentialRampToValueAtTime(slideTo, now + duration);
    }

    volume.gain.setValueAtTime(0.0001, now);
    volume.gain.exponentialRampToValueAtTime(gain, now + 0.01);
    volume.gain.exponentialRampToValueAtTime(0.0001, now + duration);

    oscillator.connect(volume);
    volume.connect(this.context.destination);
    oscillator.start(now);
    oscillator.stop(now + duration + 0.02);
  }

  start() {
    this.tone(260, 0.08, "triangle", 0.06, 520);
    setTimeout(() => this.tone(780, 0.1, "triangle", 0.045), 80);
  }

  turn() {
    this.tone(320, 0.035, "square", 0.025, 420);
  }

  eat() {
    this.tone(620, 0.08, "sine", 0.06, 1040);
  }

  crash() {
    this.tone(170, 0.24, "sawtooth", 0.06, 55);
  }
}
