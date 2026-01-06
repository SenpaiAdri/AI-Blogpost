import Navbar from "@/components/Navbar";

export default function Home() {
  return (
    <div className="h-screen w-full bg-[#131316]">
      <Navbar />
      <div className="h-full w-full flex flex-row items-center justify-center">
        <div className="h-full hidden sm:block sm:flex-[.25] md:flex-[.5] lg:flex-1"></div>
        {/* Main Content */}
        <div className="h-full flex-2
        border border-[#6A6B70] border-dashed border-b-0 border-t-0 border-x-2">
          <main className="h-full w-full flex flex-col items-center justify-center">
            <h1 className="text-4xl font-bold">Hello World</h1>
          </main>
        </div>
        <div className="h-full hidden sm:block sm:flex-[.25] md:flex-[.5] lg:flex-1"></div>
      </div>
    </div>
  );
}
