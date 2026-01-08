"use client";

import { Post } from "@/lib/types";
import Tags from "./Tags";
import Link from "next/link";

export default function BlogCard({ post }: { post: Post }) {
  const tldrItems = Array.isArray(post.tldr) ? post.tldr : [];

  return (
    <div className="relative block p-6 border border-[#393A41] rounded-2xl hover:border-[#6A6B70] transition-colors duration-200 group">
      <div className="flex flex-col h-full">
        {/* Header */}
        <h2 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors
        sm:text-xl md:text-2xl">
          <Link href={`/blog/${post.slug}`} className="before:absolute before:inset-0 focus:outline-none">
            {post.title}
          </Link>
        </h2>

        {/* Tags */}
        <div className="py-2 flex flex-row items-start justify-between mt-2 relative z-10 pointer-events-none">
          <div className="pointer-events-auto">
            <Tags tags={post.tags || []} />
          </div>
          <div className="text-xs sm:text-sm text-[#808080]">
            {new Date(post.published_at || "").toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric'
            })}
          </div>
        </div>

        {/* TL;DR Section */}
        {tldrItems.length > 0 && (
          <div className="px-4">
            <p className="text-xs sm:text-sm font-bold text-[#808080] my-2">TL;DR</p>
            <ul className="space-y-2">
              {tldrItems.map((item: string | any, index: number) => (
                <li key={index} className="flex items-start text-white text-sm sm:text-base">
                  <span className="mr-2">•</span>
                  {/* Handle both string and legacy object format just in case */}
                  <span>{typeof item === 'string' ? item : item.name}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Blog's Footer */}
        <div className="mt-6 flex items-center justify-between relative z-10">
          {post.source_url && post.source_url.length > 0 && (
            <div className="text-xs sm:text-sm font-medium text-[#808080] inline-flex items-center flex-wrap">
              {post.source_url.length > 1 ?
                <span className="mr-1">sources:</span>
                : <span className="mr-1">source:</span>
              }
              {post.source_url.map((source: any, index: number) => {
                const url = typeof source === 'string' ? null : source.url;
                const name = typeof source === 'string' ? source : (source.name || source.url);

                return (
                  <span key={index} className="inline-flex items-center">
                    {index > 0 && <span className="mx-1">|</span>}
                    {url ? (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:underline cursor-pointer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {name}
                      </a>
                    ) : (
                      <span className="text-blue-400">{name}</span>
                    )}
                  </span>
                );
              })}
            </div>
          )}
          <span className="text-xs sm:text-sm font-medium text-blue-400 group-hover:translate-x-1 transition-transform inline-flex items-center pointer-events-none whitespace-nowrap">
            Read full post
            <svg className="w-3 h-3 ml-1 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </span>
        </div>
      </div>
    </div>
  );
}
