import Image from "next/image";

export default function Navbar() {
  return (
    <div className="h-15 w-full absolute top-0 left-0 px-50 flex items-center justify-around 
    border border-[#6A6B70] border-dashed border-b-2 border-t-0 border-l-0 border-r-0">
      <Image
        src="/logo/ai_blogpost_text_dark.svg"
        alt="logo"
        width={100}
        height={100}
      />
      <p className="text-white text-lg font-bold">about us</p>
    </div>
  );
}