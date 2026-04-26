import Navbar from "@/components/Navbar";
import BackToTopButton from "@/components/BackToTopButton";
import { PostFeedSkeleton } from "@/components/PostFeed";

function TopicFilterBarSkeleton() {
  return (
    <div className="space-y-3 pb-2 animate-pulse">
      <div className="flex flex-wrap items-center gap-2">
        <span className="h-3 w-14 rounded bg-[#26262C]" />
        {Array.from({ length: 5 }).map((_, i) => (
          <span key={i} className="h-7 w-20 rounded-full bg-[#26262C]" />
        ))}
      </div>
    </div>
  );
}

export default function Loading() {
  return (
    <div className="min-h-screen w-full bg-[#131316] text-white">
      <Navbar />

      <div className="w-full flex justify-center">
        <main
          className="w-full max-w-4xl sm:border-x-2 sm:border-[#6A6B70] sm:border-dashed min-h-screen pt-19 px-4 pb-10 
        sm:pb-20 sm:pt-21
        md:px-8 md:pt-24"
        >
          <div className="w-full space-y-6">
            <TopicFilterBarSkeleton />
            <PostFeedSkeleton count={10} />
          </div>
        </main>
      </div>
      <BackToTopButton />
    </div>
  );
}
