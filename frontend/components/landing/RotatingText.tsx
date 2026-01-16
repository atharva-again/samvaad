"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface RotatingTextProps {
  words: string[];
  fonts?: string[];
  interval?: number;
  className?: string;
}

export function RotatingText({
  words,
  fonts = [],
  interval = 1200,
  className,
}: RotatingTextProps) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((prev) => (prev + 1) % words.length);
    }, interval);
    return () => clearInterval(timer);
  }, [words, interval]);

  return (
    <span className={cn("inline-grid place-items-center relative h-[1.1em] w-full align-bottom", className)}>
       <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
            key={index}
            initial={{ opacity: 0, filter: "blur(10px)", scale: 1.1 }}
            animate={{ opacity: 1, filter: "blur(0px)", scale: 1 }}
            exit={{ opacity: 0, filter: "blur(10px)", scale: 0.9, position: "absolute" }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className={cn("col-start-1 row-start-1 whitespace-nowrap", fonts[index % fonts.length])}
        >
            {words[index]}
        </motion.span>
       </AnimatePresence>
    </span>
  );
}
