"use client";

import { useEffect, useRef } from "react";

export function MouseGlow() {
  const glowRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const glow = glowRef.current;
    if (!glow || typeof window === "undefined") {
      return;
    }

    const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
    if (coarsePointer) {
      glow.style.display = "none";
      return;
    }

    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;
    let currentX = targetX;
    let currentY = targetY;
    let frameId = 0;

    const render = () => {
      currentX += (targetX - currentX) * 0.14;
      currentY += (targetY - currentY) * 0.14;
      glow.style.transform = `translate3d(${currentX - 140}px, ${currentY - 140}px, 0)`;
      frameId = window.requestAnimationFrame(render);
    };

    const handleMove = (event: MouseEvent) => {
      targetX = event.clientX;
      targetY = event.clientY;
      glow.style.opacity = "1";
    };

    const handleLeave = () => {
      glow.style.opacity = "0";
    };

    frameId = window.requestAnimationFrame(render);
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseout", handleLeave);

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseout", handleLeave);
    };
  }, []);

  return (
    <div
      ref={glowRef}
      aria-hidden="true"
      className="pointer-events-none fixed left-0 top-0 z-10 hidden h-[280px] w-[280px] rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.08)_0%,rgba(255,255,255,0.04)_28%,rgba(255,255,255,0.015)_48%,transparent_72%)] opacity-0 blur-3xl transition-opacity duration-300 md:block"
    />
  );
}
