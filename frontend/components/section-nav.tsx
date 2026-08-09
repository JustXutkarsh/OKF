"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export interface SectionNavItem {
  id: string;
  num: string;
  label: string;
}

export const SECTIONS: SectionNavItem[] = [
  { id: "section-mission", num: "01", label: "MISSION" },
  { id: "section-results", num: "04", label: "RESULTS" },
  { id: "section-debate", num: "05", label: "DEBATE" },
  { id: "section-confidence", num: "06", label: "CONFIDENCE" },
  { id: "section-sources", num: "07", label: "SOURCES" },
  { id: "section-evidence", num: "03", label: "EVIDENCE" },
  { id: "section-execution", num: "02", label: "EXECUTION" },
  { id: "section-network", num: "08", label: "NETWORK" },
];

export function SectionNav({ activeId }: { activeId?: string }) {
  const [currentActive, setCurrentActive] = useState<string>(activeId || "section-mission");

  useEffect(() => {
    const sectionElements = SECTIONS.map((s) => document.getElementById(s.id)).filter(
      (el): el is HTMLElement => el !== null
    );

    if (sectionElements.length === 0 || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (visible.length > 0) {
          setCurrentActive(visible[0].target.id);
        }
      },
      { threshold: 0.2, rootMargin: "-80px 0px -40% 0px" }
    );

    sectionElements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  function scrollToSection(id: string) {
    const el = document.getElementById(id);
    if (el) {
      const top = el.getBoundingClientRect().top + window.scrollY - 70;
      window.scrollTo({ top, behavior: "smooth" });
    }
  }

  return (
    <nav
      aria-label="Chapter sections"
      className="sticky top-12 z-20 border-y border-border/50 bg-background/95 backdrop-blur-md"
    >
      <div className="mx-auto flex max-w-[1600px] items-center gap-1 overflow-x-auto px-4 py-2 scrollbar-none">
        {SECTIONS.map((sec) => {
          const isActive = currentActive === sec.id;
          return (
            <button
              key={sec.id}
              onClick={() => scrollToSection(sec.id)}
              className={`relative flex shrink-0 items-center gap-1.5 rounded px-2.5 py-1 font-mono text-[10px] tracking-widest transition-colors ${
                isActive
                  ? "font-semibold text-foreground"
                  : "text-muted-foreground/60 hover:text-foreground"
              }`}
            >
              <span
                className={`text-[9px] ${
                  isActive ? "text-cyan-400 font-bold" : "text-muted-foreground/40"
                }`}
              >
                {sec.num}
              </span>
              <span>{sec.label}</span>
              {isActive && (
                <motion.div
                  layoutId="activeSectionIndicator"
                  className="absolute inset-x-0 -bottom-[9px] h-[2px] bg-cyan-400"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
