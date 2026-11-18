"use client";

import { motion, useScroll, useTransform, useMotionValue, useSpring } from "framer-motion";
import { useRef } from "react";

export function Footer() {
  const { scrollYProgress } = useScroll();
  const containerRef = useRef<HTMLDivElement>(null);

  // Scroll Reveal Effects:
  // Blur: Starts blurry (10px) and focuses (0px) as we reach the bottom
  const textBlur = useTransform(scrollYProgress, [0.85, 1], ["10px", "0px"]);
  // Scale: Starts slightly zoomed out (0.9) and scales to neutral (1)
  const textScale = useTransform(scrollYProgress, [0.85, 1], [0.9, 1]);
  // Opacity: Fades in
  const textOpacity = useTransform(scrollYProgress, [0.85, 1], [0.2, 1]);

  // Mouse Parallax
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const springConfig = { damping: 20, stiffness: 100, mass: 0.5 };
  const springX = useSpring(mouseX, springConfig);
  const springY = useSpring(mouseY, springConfig);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const { left, top, width, height } = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - left - width / 2) / (width / 2);
    const y = (e.clientY - top - height / 2) / (height / 2);
    mouseX.set(x * -30);
    mouseY.set(y * -15);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  return (
    <footer
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="fixed bottom-0 left-0 w-full h-[500px] md:h-[600px] z-0 overflow-hidden bg-black flex flex-col justify-between pt-20 pb-10"
    >
      {/* Vignette Background */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_100%,_rgba(255,255,255,0.03),_transparent_70%)] pointer-events-none" />

      <div className="mx-auto max-w-4xl px-6 text-center z-10 relative flex-1 flex flex-col justify-start pt-10">
        {/* Quote Section */}
        <p className="mb-10 text-2xl md:text-3xl lg:text-4xl font-[family-name:var(--font-playfair)] font-light text-white/80 leading-relaxed tracking-wide antialiased">
          Intelligence is the dialogue between
          <br />
          knowledge and curiosity.
        </p>

        {/* Navigation/Utility Section */}
        <div className="flex flex-col items-center gap-6">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="group relative flex items-center justify-center p-2 text-white/40 hover:text-white transition-colors duration-300"
            aria-label="GitHub"
          >
            <span className="absolute inset-0 bg-white/10 rounded-full scale-0 group-hover:scale-100 transition-transform duration-300 ease-out" />
            <svg
              className="relative z-10 h-6 w-6"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M12 .5a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.05c-3.34.73-4.04-1.42-4.04-1.42-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.74.08-.74 1.2.09 1.84 1.23 1.84 1.23 1.07 1.83 2.8 1.3 3.48.99.11-.77.42-1.3.76-1.6-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.38 1.23-3.22-.12-.3-.53-1.52.12-3.17 0 0 1-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.3-1.55 3.3-1.23 3.3-1.23.65 1.65.24 2.87.12 3.17.77.84 1.23 1.91 1.23 3.22 0 4.62-2.8 5.64-5.48 5.94.43.37.81 1.1.81 2.22v3.29c0 .32.22.7.83.58A12 12 0 0 0 12 .5Z" />
            </svg>
          </a>

          <div className="text-[10px] font-bold tracking-[0.2em] uppercase text-white/20">
            © 2026 Samvaad
          </div>
        </div>
      </div>

      {/* Large Brand Text - Editorial Ghost Outline */}
      <div className="w-full flex justify-center items-end select-none pointer-events-none absolute bottom-0 left-0 overflow-hidden pb-4">
        <motion.div style={{ x: springX, y: springY }} className="relative">
          <motion.h1
            style={{
              filter: useTransform(textBlur, (v) => `blur(${v})`),
              scale: textScale,
              opacity: textOpacity,
              WebkitTextStroke: "1px rgba(255, 255, 255, 0.15)",
            }}
            className="text-[15vw] md:text-[18vw] leading-[0.8] font-[family-name:var(--font-outfit)] font-bold tracking-tight text-transparent whitespace-nowrap uppercase translate-y-[15%]"
          >
            SAMVAAD
          </motion.h1>
        </motion.div>
      </div>
    </footer>
  );
}
