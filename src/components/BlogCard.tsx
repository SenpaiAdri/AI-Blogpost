import { Post } from "@/lib/types";
import Tags from "./Tags";
import Link from "next/link";

export default function BlogCard({ post }: { post: Post }) {
    // Helper to safely get TLDR items.
    // We assume it's string[], but let's be safe.
    const tldrItems = Array.isArray(post.tldr) ? post.tldr : [];

    return (
        <Link 
            href={`/blog/${post.slug}`}
            className="block p-6 border border-[#393A41] rounded-2xl hover:border-[#6A6B70] transition-colors duration-200 group"
        >
            <div className="flex flex-col h-full">
                {/* Header */}
                <h2 className="text-2xl font-bold text-white group-hover:text-blue-400 transition-colors">
                    {post.title}
                </h2>

                {/* Tags */}
                <div className="mb-3 flex flex-row items-start justify-between mt-5">
                    <Tags tags={post.tags || []} />
                    <div className="mt-2 text-sm text-[#808080]">
                        {new Date(post.published_at || "").toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                        })}
                    </div>
                </div>

                {/* TL;DR Section (Replaces Excerpt) */}
                {tldrItems.length > 0 && (
                    <div className="mb-6 bg-[#2c2c31]/50 p-4 rounded-lg border border-[#3e3e44]/50">
                        <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">TL;DR</p>
                        <ul className="space-y-2">
                            {tldrItems.map((item: string | any, index: number) => (
                                <li key={index} className="flex items-start text-gray-300 text-sm">
                                    <span className="mr-2 text-blue-400 mt-0.5">•</span>
                                    {/* Handle both string and legacy object format just in case */}
                                    <span>{typeof item === 'string' ? item : item.name}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Footer */}
                <div className="mt-auto flex items-center justify-end">
                    <span className="text-sm font-medium text-blue-400 group-hover:translate-x-1 transition-transform inline-flex items-center">
                        Read full post 
                        <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                    </span>
                </div>
            </div>
        </Link>
    );
}
