export class Sound {
  constructor() {
    this.context = null;
    this.enabled = true;
  }

  unlock() {
    if (!this.context) {
      this.context = new AudioContext();
    }
    if (this.context.state === "suspended") {
      this.context.resume();
    }
  }

  tone({ frequency, duration = 0.12, type = "sine", gain = 0.08, slideTo = null }) {
    if (!this.enabled) {
      return;
    }
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
    volume.gain.exponentialRampToValueAtTime(gain, now + 0.015);
    volume.gain.exponentialRampToValueAtTime(0.0001, now + duration);

    oscillator.connect(volume);
    volume.connect(this.context.destination);
    oscillator.start(now);
    oscillator.stop(now + duration + 0.03);
  }

  start() {
    this.tone({ frequency: 220, duration: 0.1, type: "triangle", gain: 0.07, slideTo: 440 });
    setTimeout(() => this.tone({ frequency: 660, duration: 0.14, type: "triangle", gain: 0.06 }), 90);
  }

  energy() {
    this.tone({ frequency: 740, duration: 0.08, type: "sine", gain: 0.05, slideTo: 980 });
  }

  power() {
    this.tone({ frequency: 360, duration: 0.16, type: "sawtooth", gain: 0.045, slideTo: 920 });
  }

  shield() {
    this.tone({ frequency: 180, duration: 0.18, type: "square", gain: 0.05, slideTo: 90 });
  }

  gameOver() {
    this.tone({ frequency: 220, duration: 0.28, type: "sawtooth", gain: 0.055, slideTo: 70 });
  }
}
