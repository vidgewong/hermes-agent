import { useEffect, useRef } from "react";
import { useTheme } from "@/themes";

export function MercedesStarfield() {
  const { themeName } = useTheme();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    if (themeName !== "mercedes-benz") return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

    function resizeCanvas() {
      const dpr = window.devicePixelRatio || 1;
      canvas!.width = window.innerWidth * dpr;
      canvas!.height = window.innerHeight * dpr;
      ctx!.scale(dpr, dpr);
    }

    class Star {
      type: number;
      x = 0;
      y = 0;
      size = 0;
      baseAlpha = 0;
      alpha = 0;
      speed = 0;
      hasRing = false;
      depth = 0;
      phase = 0;
      flareProgress = 0;
      isFlaring = false;
      driftX = 0;
      driftY = 0;

      constructor(type: number) {
        this.type = type;
        this.phase = Math.random() * Math.PI * 2;
        this.reset();
      }

      reset() {
        this.x = Math.random() * window.innerWidth;
        this.y = Math.random() * window.innerHeight;
        this.flareProgress = 0;
        this.isFlaring = false;

        const angle = Math.random() * Math.PI * 2;
        if (this.type === 0) {
          this.size = Math.random() * 1.5 + 2;
          this.baseAlpha = Math.random() * 0.08 + 0.03;
          this.speed = Math.random() * 0.008 + 0.003;
          this.hasRing = false;
          this.depth = 0.2;
          const drift = Math.random() * 0.08 + 0.02;
          this.driftX = Math.cos(angle) * drift;
          this.driftY = Math.sin(angle) * drift;
        } else if (this.type === 1) {
          this.size = Math.random() * 3 + 3;
          this.baseAlpha = Math.random() * 0.12 + 0.06;
          this.speed = Math.random() * 0.015 + 0.007;
          this.hasRing = true;
          this.depth = 0.4;
          const drift = Math.random() * 0.06 + 0.015;
          this.driftX = Math.cos(angle) * drift;
          this.driftY = Math.sin(angle) * drift;
        } else {
          this.size = Math.random() * 4 + 6;
          this.baseAlpha = Math.random() * 0.15 + 0.1;
          this.speed = Math.random() * 0.01 + 0.004;
          this.hasRing = true;
          this.depth = 0.7;
          const drift = Math.random() * 0.04 + 0.01;
          this.driftX = Math.cos(angle) * drift;
          this.driftY = Math.sin(angle) * drift;
        }
      }

      update() {
        this.phase += this.speed;
        this.alpha =
          this.baseAlpha + Math.sin(this.phase) * (this.baseAlpha * 0.4);

        this.x += this.driftX;
        this.y += this.driftY;

        const w = window.innerWidth;
        const h = window.innerHeight;
        if (this.x < -20) this.x = w + 20;
        if (this.x > w + 20) this.x = -20;
        if (this.y < -20) this.y = h + 20;
        if (this.y > h + 20) this.y = -20;

        if (this.type === 2 && !this.isFlaring && Math.random() < 0.002) {
          this.isFlaring = true;
          this.flareProgress = 0;
        }

        if (this.isFlaring) {
          this.flareProgress += 0.015;
          if (this.flareProgress > 1) {
            this.isFlaring = false;
            this.flareProgress = 0;
          }
          const flarePeak = 0.35;
          if (this.flareProgress < 0.15) {
            this.alpha += (flarePeak - this.alpha) * (this.flareProgress / 0.15);
          } else {
            this.alpha +=
              (flarePeak - this.alpha) *
              (1 - (this.flareProgress - 0.15) / 0.85) *
              0.6;
          }
        }
      }

      draw(c: CanvasRenderingContext2D) {
        const renderX = this.x + mouse.x * this.depth;
        const renderY = this.y + mouse.y * this.depth;

        c.save();
        c.translate(renderX, renderY);

        if (this.isFlaring && this.type === 2) {
          c.shadowBlur = (1 - this.flareProgress) * 12;
          c.shadowColor = "rgba(255, 255, 255, 0.3)";
        }

        if (this.hasRing) {
          c.beginPath();
          c.arc(0, 0, this.size, 0, Math.PI * 2);
          c.strokeStyle = `rgba(220, 230, 245, ${this.alpha * 0.2})`;
          c.lineWidth = this.size * 0.04;
          c.stroke();
        }

        const tips = [-Math.PI / 2, Math.PI / 6, (5 * Math.PI) / 6];
        const valleys = [-Math.PI / 6, Math.PI / 2, (7 * Math.PI) / 6];
        const rOuter = this.size * 0.88;
        const rInner = this.size * 0.12;

        for (let i = 0; i < 3; i++) {
          c.beginPath();
          c.moveTo(0, 0);
          c.lineTo(Math.cos(tips[i]) * rOuter, Math.sin(tips[i]) * rOuter);
          c.lineTo(
            Math.cos(valleys[i]) * rInner,
            Math.sin(valleys[i]) * rInner,
          );
          c.closePath();
          c.fillStyle = `rgba(255, 255, 255, ${this.alpha})`;
          c.fill();

          c.beginPath();
          c.moveTo(0, 0);
          c.lineTo(Math.cos(tips[i]) * rOuter, Math.sin(tips[i]) * rOuter);
          const prevValley = (i - 1 + 3) % 3;
          c.lineTo(
            Math.cos(valleys[prevValley]) * rInner,
            Math.sin(valleys[prevValley]) * rInner,
          );
          c.closePath();
          c.fillStyle = `rgba(195, 205, 220, ${this.alpha * 0.55})`;
          c.fill();
        }

        c.restore();
      }
    }

    let stars: Star[] = [];

    function initStars() {
      stars = [];
      const desktop = window.innerWidth > 1024;
      const countType0 = desktop ? 110 : 50;
      const countType1 = desktop ? 45 : 22;
      const countType2 = desktop ? 14 : 7;

      for (let i = 0; i < countType0; i++) stars.push(new Star(0));
      for (let i = 0; i < countType1; i++) stars.push(new Star(1));
      for (let i = 0; i < countType2; i++) stars.push(new Star(2));
    }

    function animate() {
      mouse.x += (mouse.targetX - mouse.x) * 0.08;
      mouse.y += (mouse.targetY - mouse.y) * 0.08;

      ctx!.clearRect(0, 0, window.innerWidth, window.innerHeight);

      for (const star of stars) {
        star.update();
        star.draw(ctx!);
      }

      animRef.current = requestAnimationFrame(animate);
    }

    function onResize() {
      resizeCanvas();
      initStars();
    }

    function onMouseMove(e: MouseEvent) {
      mouse.targetX = (e.clientX - window.innerWidth / 2) * 0.04;
      mouse.targetY = (e.clientY - window.innerHeight / 2) * 0.04;
    }

    resizeCanvas();
    initStars();
    animRef.current = requestAnimationFrame(animate);

    window.addEventListener("resize", onResize);
    window.addEventListener("mousemove", onMouseMove);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("mousemove", onMouseMove);
    };
  }, [themeName]);

  if (themeName !== "mercedes-benz") return null;

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-0"
      aria-hidden
    />
  );
}
