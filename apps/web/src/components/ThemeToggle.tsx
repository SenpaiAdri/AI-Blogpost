"use client";

import { Moon, Sun } from "lucide-react";
import { useCallback, type MouseEvent } from "react";
import { flushSync } from "react-dom";
import { useTheme } from "./ThemeProvider";

type ViewTransitionDocument = Document & {
  startViewTransition?: (callback: () => void) => {
    ready: Promise<void>;
    finished: Promise<void>;
    updateCallbackDone: Promise<void>;
  };
};

export default function ThemeToggle() {
  const { toggleTheme } = useTheme();

  const handleToggle = useCallback(
    async (e: MouseEvent<HTMLButtonElement>) => {
      const doc = document as ViewTransitionDocument;

      // Fall back to an instant swap without the API or for reduced motion.
      if (
        !doc.startViewTransition ||
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ) {
        toggleTheme();
        return;
      }

      // Keyboard activation reports 0,0 — fall back to the button center.
      const rect = e.currentTarget.getBoundingClientRect();
      const fromKeyboard = e.clientX === 0 && e.clientY === 0;
      const x = fromKeyboard ? rect.left + rect.width / 2 : e.clientX;
      const y = fromKeyboard ? rect.top + rect.height / 2 : e.clientY;

      const transition = doc.startViewTransition(() => {
        flushSync(() => toggleTheme());
      });

      try {
        await transition.ready;
        const endRadius = Math.hypot(
          Math.max(x, window.innerWidth - x),
          Math.max(y, window.innerHeight - y),
        );
        document.documentElement.animate(
          {
            clipPath: [
              `circle(0px at ${x}px ${y}px)`,
              `circle(${endRadius}px at ${x}px ${y}px)`,
            ],
          },
          {
            duration: 700,
            easing: "ease-out",
            pseudoElement: "::view-transition-new(root)",
          },
        );
      } catch {
        // Transition aborted — theme is already applied, nothing to do.
      }
    },
    [toggleTheme],
  );

  return (
    <button
      type="button"
      onClick={handleToggle}
      aria-label="Toggle theme"
      title="Toggle theme"
      className="inline-flex h-9 w-9 items-center justify-center text-ink-muted transition-colors hover:border-brand hover:text-brand"
    >
      {/* CSS-driven icon swap avoids hydration mismatch. */}
      <Sun size={22} className="dark:hidden" />
      <Moon size={22} className="hidden dark:block" />
    </button>
  );
}
