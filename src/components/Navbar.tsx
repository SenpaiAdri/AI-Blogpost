import Image from "next/image";

export default function Navbar() {
  return (
    <div className="h-15 w-full absolute top-0 left-0 flex items-center justify-around">
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