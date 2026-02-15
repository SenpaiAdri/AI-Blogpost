import Image from "next/image";
import TransitionLink from "./TransitionLink";

export default function Navbar() {
  return (
    <div className="fixed top-0 left-0 w-full z-50 bg-[#131316]/10 backdrop-blur-md border-b-2 border-[#6A6B70] border-dashed">
      <div className="w-full flex justify-center">
        <div className="w-full max-w-4xl flex items-center justify-between px-4 sm:px-8 py-2">
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
    
          <TransitionLink href="/about" className="text-white text-base sm:text-lg font-bold">about us</TransitionLink>
        </div>
      </div>
    </div>
  );
}
