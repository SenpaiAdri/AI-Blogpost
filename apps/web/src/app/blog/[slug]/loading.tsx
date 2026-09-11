import Navbar from "@/components/Navbar";
import BlogPostSkeleton from "@/components/BlogPostSkeleton";

export default function BlogPostLoading() {
  return (
    <div className="min-h-screen w-full bg-[#131316] text-white">
      <Navbar />

      <div className="w-full flex justify-center">
        <main className="w-full max-w-4xl sm:border-x-2 sm:border-[#6A6B70] sm:border-dashed min-h-screen pt-24 px-6 sm:px-8 pb-20">
          <BlogPostSkeleton />
        </main>
      </div>
    </div>
  );
}
