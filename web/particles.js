/* ═══════════════════════════════════════════════════════
   PlantGuard AI — Organic Leaf Particle Background
   Floating leaves, spores, and pollen drifting gently
   ═══════════════════════════════════════════════════════ */

(function () {
  const canvas = document.getElementById("particleCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const CONFIG = {
    leaves: 18,
    spores: 30,
    pollen: 15,
    driftSpeed: 0.25,
    swayAmount: 0.4,
    linkDistance: 100,
    linkOpacity: 0.04,
  };

  let particles = [];
  let w, h, animId, t = 0;

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  window.addEventListener("resize", resize);
  resize();

  /* ── Draw a tiny leaf shape ── */
  function drawLeaf(x, y, size, angle, opacity, color) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.globalAlpha = opacity;

    // Leaf body
    ctx.beginPath();
    ctx.moveTo(0, -size);
    ctx.bezierCurveTo(size * 0.6, -size * 0.6, size * 0.5, size * 0.4, 0, size);
    ctx.bezierCurveTo(-size * 0.5, size * 0.4, -size * 0.6, -size * 0.6, 0, -size);
    ctx.fillStyle = color;
    ctx.fill();

    // Center vein
    ctx.beginPath();
    ctx.moveTo(0, -size * 0.8);
    ctx.lineTo(0, size * 0.7);
    ctx.strokeStyle = color;
    ctx.globalAlpha = opacity * 0.4;
    ctx.lineWidth = 0.4;
    ctx.stroke();

    ctx.restore();
  }

  /* ── Draw a spore (small fuzzy circle) ── */
  function drawSpore(x, y, r, opacity, color) {
    // Glow halo
    const grad = ctx.createRadialGradient(x, y, 0, x, y, r * 3);
    grad.addColorStop(0, color.replace(")", `, ${opacity * 0.5})`).replace("rgb", "rgba"));
    grad.addColorStop(1, "transparent");
    ctx.beginPath();
    ctx.arc(x, y, r * 3, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();

    // Core
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = color.replace(")", `, ${opacity})`).replace("rgb", "rgba");
    ctx.fill();
  }

  /* ── Draw pollen grain (tiny star/cross) ── */
  function drawPollen(x, y, size, angle, opacity) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.globalAlpha = opacity;

    const arms = 4;
    for (let i = 0; i < arms; i++) {
      const a = (Math.PI * 2 / arms) * i;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(Math.cos(a) * size, Math.sin(a) * size);
      ctx.strokeStyle = "rgb(167, 243, 208)";
      ctx.lineWidth = 0.6;
      ctx.stroke();

      // Tiny dot at tip
      ctx.beginPath();
      ctx.arc(Math.cos(a) * size, Math.sin(a) * size, 0.6, 0, Math.PI * 2);
      ctx.fillStyle = "rgb(167, 243, 208)";
      ctx.fill();
    }

    ctx.restore();
  }

  /* ── Particle types ── */
  const COLORS = [
    "rgb(16, 185, 129)",   // emerald-500
    "rgb(52, 211, 153)",   // emerald-400
    "rgb(110, 231, 183)",  // emerald-300
    "rgb(6, 95, 70)",      // emerald-800
    "rgb(4, 120, 87)",     // emerald-700
  ];

  class Particle {
    constructor(type) {
      this.type = type;
      this.reset();
    }

    reset() {
      this.x = Math.random() * w;
      this.y = Math.random() * h;
      this.color = COLORS[Math.floor(Math.random() * COLORS.length)];
      this.pulsePhase = Math.random() * Math.PI * 2;

      if (this.type === "leaf") {
        this.size = 5 + Math.random() * 8;
        this.opacity = 0.08 + Math.random() * 0.18;
        this.vx = (Math.random() - 0.5) * CONFIG.driftSpeed;
        this.vy = CONFIG.driftSpeed * 0.3 + Math.random() * CONFIG.driftSpeed * 0.5;
        this.rotSpeed = (Math.random() - 0.5) * 0.008;
        this.angle = Math.random() * Math.PI * 2;
        this.swayOffset = Math.random() * Math.PI * 2;
        this.swaySpeed = 0.008 + Math.random() * 0.012;
      } else if (this.type === "spore") {
        this.r = 1 + Math.random() * 1.5;
        this.opacity = 0.12 + Math.random() * 0.3;
        this.vx = (Math.random() - 0.5) * CONFIG.driftSpeed * 1.2;
        this.vy = (Math.random() - 0.5) * CONFIG.driftSpeed * 0.8;
        this.pulseSpeed = 0.01 + Math.random() * 0.02;
      } else {
        // pollen
        this.size = 2 + Math.random() * 3;
        this.opacity = 0.1 + Math.random() * 0.2;
        this.vx = (Math.random() - 0.5) * CONFIG.driftSpeed * 0.6;
        this.vy = -CONFIG.driftSpeed * 0.2 - Math.random() * CONFIG.driftSpeed * 0.3;
        this.rotSpeed = (Math.random() - 0.5) * 0.015;
        this.angle = Math.random() * Math.PI * 2;
      }
    }

    update() {
      if (this.type === "leaf") {
        // Gentle sway
        this.x += this.vx + Math.sin(t * this.swaySpeed + this.swayOffset) * CONFIG.swayAmount * 0.3;
        this.y += this.vy;
        this.angle += this.rotSpeed;
        // Gentle opacity pulse
        this.currentOpacity = this.opacity * (0.7 + 0.3 * Math.sin(t * 0.008 + this.pulsePhase));
      } else if (this.type === "spore") {
        this.x += this.vx;
        this.y += this.vy;
        this.currentOpacity = this.opacity * (0.5 + 0.5 * Math.sin(t * this.pulseSpeed + this.pulsePhase));
      } else {
        // Pollen floats upward with drift
        this.x += this.vx + Math.sin(t * 0.01 + this.pulsePhase) * 0.15;
        this.y += this.vy;
        this.angle += this.rotSpeed;
        this.currentOpacity = this.opacity * (0.6 + 0.4 * Math.sin(t * 0.012 + this.pulsePhase));
      }

      // Wrap edges
      if (this.x < -20) this.x = w + 20;
      if (this.x > w + 20) this.x = -20;
      if (this.y < -20) this.y = h + 20;
      if (this.y > h + 20) this.y = -20;
    }

    draw() {
      if (this.type === "leaf") {
        drawLeaf(this.x, this.y, this.size, this.angle, this.currentOpacity, this.color);
      } else if (this.type === "spore") {
        drawSpore(this.x, this.y, this.r, this.currentOpacity, this.color);
      } else {
        drawPollen(this.x, this.y, this.size, this.angle, this.currentOpacity);
      }
    }
  }

  /* ── Vine-like connections between nearby spores ── */
  function drawVines() {
    const spores = particles.filter(p => p.type === "spore");
    for (let i = 0; i < spores.length; i++) {
      for (let j = i + 1; j < spores.length; j++) {
        const dx = spores[i].x - spores[j].x;
        const dy = spores[i].y - spores[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < CONFIG.linkDistance) {
          const alpha = CONFIG.linkOpacity * (1 - dist / CONFIG.linkDistance);
          const mx = (spores[i].x + spores[j].x) / 2;
          const my = (spores[i].y + spores[j].y) / 2 - dist * 0.1;

          ctx.beginPath();
          ctx.moveTo(spores[i].x, spores[i].y);
          ctx.quadraticCurveTo(mx, my, spores[j].x, spores[j].y);
          ctx.strokeStyle = `rgba(16, 185, 129, ${alpha})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
  }

  /* ── Init ── */
  function init() {
    particles = [];
    for (let i = 0; i < CONFIG.leaves; i++) particles.push(new Particle("leaf"));
    for (let i = 0; i < CONFIG.spores; i++) particles.push(new Particle("spore"));
    for (let i = 0; i < CONFIG.pollen; i++) particles.push(new Particle("pollen"));
  }

  /* ── Loop ── */
  function animate() {
    t++;
    ctx.clearRect(0, 0, w, h);

    for (const p of particles) {
      p.update();
      p.draw();
    }

    drawVines();
    animId = requestAnimationFrame(animate);
  }

  /* ── Pause when hidden ── */
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      cancelAnimationFrame(animId);
    } else {
      animate();
    }
  });

  init();
  animate();
})();
