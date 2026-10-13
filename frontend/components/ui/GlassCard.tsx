"use client";

import { motion } from "framer-motion";
import { type ReactNode } from "react";
import clsx from "clsx";

export function GlassCard({
  children,
  className,
  glow = false,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  glow?: boolean;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
      whileHover={{ y: -3 }}
      className={clsx(
        "rounded-3xl border p-5 backdrop-blur-xl transition-shadow",
        "bg-[var(--surface-glass)] border-[var(--border-glass)]",
        "hover:bg-[var(--surface-glass-hover)]",
        glow && "shadow-[0_0_40px_-12px_rgba(124,58,237,0.45)]",
        className
      )}
    >
      {children}
    </motion.div>
  );
}
