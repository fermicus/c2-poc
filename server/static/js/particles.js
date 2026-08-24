const particleConfig = {
  enable:              true,
  chars:               [".", "#", "~", ":", "'", "*", "+", "×"],
  mobileBreakpoint:    760,
  count:               { desktop: 80, mobile: 30 },
  opacity:             [0.08, 0.25],
  driftX:              [-0.15, 0.15],
  driftY:              [-0.45, -0.1],
  speed:               [0.02, 0.06],
  pointerInfluenceRadius: 130,
};

function sample(arr)              { return arr[Math.floor(Math.random() * arr.length)]; }
function randomBetween(min, max)  { return min + Math.random() * (max - min); }

function resetParticle(p, anywhere) {
  const w = window.innerWidth, h = window.innerHeight;
  p.x      = randomBetween(0, w);
  p.y      = anywhere ? randomBetween(0, h) : h + randomBetween(4, 24);
  p.driftX = randomBetween(...particleConfig.driftX);
  p.driftY = randomBetween(...particleConfig.driftY);
  p.opacity = randomBetween(...particleConfig.opacity);
  p.phase  = randomBetween(0, Math.PI * 2);
  p.speed  = randomBetween(...particleConfig.speed);
  p.el.textContent = sample(particleConfig.chars);
}

function createParticle(layer) {
  const el = document.createElement("span");
  layer.appendChild(el);
  const p = { el, x: 0, y: 0, driftX: 0, driftY: 0, opacity: 0, phase: 0, speed: 0 };
  resetParticle(p, true);
  return p;
}

function stepParticle(p, pointer, motionStep) {
  p.x += p.driftX * motionStep;
  p.y += p.driftY * motionStep;

  if (Number.isFinite(pointer.x)) {
    const dx   = p.x - pointer.x;
    const dy   = p.y - pointer.y;
    const dist = Math.hypot(dx, dy);
    const r    = particleConfig.pointerInfluenceRadius;
    if (dist < r && dist > 0) {
      const force = (1 - dist / r) ** 2;
      p.x += (dx / dist) * force * 1.8;
      p.y += (dy / dist) * force * 1.2;
    }
  }

  p.phase += p.speed * motionStep;
  const flicker   = 0.72 + Math.sin(Date.now() * 0.0017 + p.phase) * 0.28;
  p.el.style.opacity   = (p.opacity * flicker).toFixed(3);
  p.el.style.transform = `translate3d(${p.x.toFixed(2)}px,${p.y.toFixed(2)}px,0)`;

  const w = window.innerWidth, h = window.innerHeight;
  if (p.y < -24 || p.y > h + 24 || p.x < -24 || p.x > w + 24) {
    resetParticle(p, false);
  }
}

function installAmbientParticles() {
  if (!particleConfig.enable) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (document.querySelector(".ascii-particles")) return;

  const layer = document.createElement("div");
  layer.className = "ascii-particles";
  layer.setAttribute("aria-hidden", "true");
  document.body.prepend(layer);

  const isMobile = window.matchMedia(`(max-width: ${particleConfig.mobileBreakpoint}px)`).matches;
  const count    = isMobile ? particleConfig.count.mobile : particleConfig.count.desktop;
  const particles = Array.from({ length: count }, () => createParticle(layer));

  const pointer = { x: NaN, y: NaN };
  if (!isMobile) {
    window.addEventListener("pointermove",  e => { pointer.x = e.clientX; pointer.y = e.clientY; }, { passive: true });
    window.addEventListener("pointerleave", ()  => { pointer.x = NaN; pointer.y = NaN; },            { passive: true });
  }

  window.addEventListener("resize", () => particles.forEach(p => resetParticle(p, true)), { passive: true });

  let running = true, rafId = 0, lastTime = 0;

  function frame(time) {
    rafId = 0;
    if (!running) return;
    const elapsed = lastTime === 0 ? 16 : Math.min(96, Math.max(1, time - lastTime));
    lastTime = time;
    particles.forEach(p => stepParticle(p, pointer, elapsed / 16));
    rafId = requestAnimationFrame(frame);
  }

  function start() { if (rafId === 0) { running = true; lastTime = 0; rafId = requestAnimationFrame(frame); } }
  function stop()  { running = false; if (rafId !== 0) { cancelAnimationFrame(rafId); rafId = 0; } }

  start();
  document.addEventListener("visibilitychange", () =>
    document.visibilityState === "visible" ? start() : stop()
  );
}

installAmbientParticles();
