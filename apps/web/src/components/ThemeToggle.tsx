"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "./ThemeProvider";

export default function ThemeToggle() {
  const { toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label="Toggle theme"
      className="inline-flex h-9 w-9 items-center justify-center text-ink-muted transition-colors hover:border-brand hover:text-brand"
    >
      {/* CSS-driven icon swap avoids hydration mismatch. */}
      <Sun size={22} className="dark:hidden" />
      <Moon size={22} className="hidden dark:block" />
    </button>
  );
}
