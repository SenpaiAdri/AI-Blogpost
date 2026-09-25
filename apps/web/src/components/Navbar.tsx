"use client";

import Image from "next/image";
import { usePathname } from "next/navigation";
import TransitionLink from "./TransitionLink";
import ThemeToggle from "./ThemeToggle";

export default function Navbar() {
  const pathname = usePathname();
  const isAbout = pathname === "/about";
  const isHome = pathname === "/";
  const isTopics = pathname === "/topics";
  const isBlog = pathname.startsWith("/blog");

  return (
    <div className="fixed top-0 left-0 w-full z-50 bg-surface/10 backdrop-blur-md border-b-2 border-line-strong border-dashed">
      <div className="w-full flex justify-center">
        <div className="w-full flex items-center justify-between px-4 sm:px-8 lg:px-16 xl:px-24 py-2">
          {/* Logo Area — CSS-driven swap avoids hydration mismatch. */}
          <div className="relative w-[120px] h-[50px]">
            <TransitionLink href="/">
              <Image
                src="/logo/ai_blogpost_text_light.svg"
                alt="logo"
                fill
                className="object-contain object-left dark:hidden"
                priority
                unoptimized
              />
              <Image
                src="/logo/ai_blogpost_text_dark.svg"
                alt="logo"
                fill
                className="object-contain object-left hidden dark:block"
                priority
                unoptimized
              />
            </TransitionLink>
          </div>

          {/* Navigation Links */}
          <div className="flex items-center gap-4 sm:gap-6">
            <ThemeToggle />
            <TransitionLink
              href="/"
              className={`text-sm sm:text-base font-bold uppercase tracking-wider transition-colors ${isHome || isBlog
                ? "text-ink-bright"
                : "text-ink-faint hover:text-ink-bright"
                }`}
            >
              blog
              {(isHome || isBlog) && (
                <span className="block h-[2px] mt-0.5 border-b-2 border-dashed border-brand" />
              )}
            </TransitionLink>

            <TransitionLink
              href="/topics"
              className={`text-sm sm:text-base font-bold uppercase tracking-wider transition-colors ${isTopics
                ? "text-ink-bright"
                : "text-ink-faint hover:text-ink-bright"
                }`}
            >
              topics
              {isTopics && (
                <span className="block h-[2px] mt-0.5 border-b-2 border-dashed border-brand" />
              )}
            </TransitionLink>

            <TransitionLink
              href="/about"
              className={`text-sm sm:text-base font-bold uppercase tracking-wider transition-colors ${isAbout
                ? "text-ink-bright"
                : "text-ink-faint hover:text-ink-bright"
                }`}
            >
              about
              {isAbout && (
                <span className="block h-[2px] mt-0.5 border-b-2 border-dashed border-brand" />
              )}
            </TransitionLink>
          </div>
        </div>
      </div>
    </div>
  );
}
