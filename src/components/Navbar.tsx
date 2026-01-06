import Image from "next/image";

export default function Navbar() {
  return (
    <div className="h-18 w-full absolute top-0 left-0 flex flex-row items-center justify-center
    border border-[#6A6B70] border-dashed border-b-2 border-t-0 border-x-0">
      <div className="h-full hidden sm:block sm:flex-[.25] md:flex-[.5] lg:flex-1"></div>

      {/* Main NavbarContent */}
      <div className="flex-2 flex flex-row items-center justify-between px-8
      sm:px-10 md:px-15 lg:px-20">
        <div className="relative w-[120px] h-[130px]">
          <Image
            src="/logo/ai_blogpost_text_dark.svg"
            alt="logo"
            fill
            className="object-contain"
            priority
            unoptimized
          />
        </div>
        <p className="text-white text-lg font-bold">about us</p>
      </div>
      <div className="h-full hidden sm:block sm:flex-[.25] md:flex-[.5] lg:flex-1"></div>
    </div>
  );
}