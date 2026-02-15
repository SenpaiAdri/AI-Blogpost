"use client";

import Image from "next/image";
import { usePathname } from "next/navigation";
import TransitionLink from "./TransitionLink";

export default function Navbar() {
  const pathname = usePathname();
  const isAbout = pathname === "/about";
  const isHome = pathname === "/";
  const isBlog = pathname.startsWith("/blog");

  return (
    <div className="fixed top-0 left-0 w-full z-50 bg-[#131316]/10 backdrop-blur-md border-b-2 border-[#6A6B70] border-dashed">
      <div className="w-full flex justify-center">
        <div className="w-full flex items-center justify-between px-4 sm:px-8 lg:px-16 xl:px-24 py-2">
          {/* Logo Area */}
          <div className="relative w-[120px] h-[50px]">
            <TransitionLink href="/">
              <Image
                src="/logo/ai_blogpost_text_dark.svg"
                alt="logo"
                fill
                className="object-contain object-left"
                priority
                unoptimized
              />
            </TransitionLink>
          </div>

          {/* Navigation Links */}
          <div className="flex items-center gap-6">
            <TransitionLink
              href="/"
              className={`text-sm sm:text-base font-bold uppercase tracking-wider transition-colors ${isHome || isBlog
                ? "text-white"
                : "text-[#6A6B70] hover:text-white"
                }`}
            >
              blog
              {(isHome || isBlog) && (
                <span className="block h-[2px] mt-0.5 border-b-2 border-dashed border-red-500" />
              )}
            </TransitionLink>

            <TransitionLink
              href="/about"
              className={`text-sm sm:text-base font-bold uppercase tracking-wider transition-colors ${isAbout
                ? "text-white"
                : "text-[#6A6B70] hover:text-white"
                }`}
            >
              about
              {isAbout && (
                <span className="block h-[2px] mt-0.5 border-b-2 border-dashed border-red-500" />
              )}
            </TransitionLink>
          </div>
        </div>
      </div>
    </div>
  );
}
