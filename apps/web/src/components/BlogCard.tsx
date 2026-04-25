"use client";

import { Post } from "@/lib/types";
import Tags from "./Tags";
import TransitionLink from "./TransitionLink";
import { formatDate, formatSource } from "@/lib/utils";
import { ChevronRight, ArrowRight } from "lucide-react";

export default function BlogCard({ post }: { post: Post }) {
  const tldrItems = Array.isArray(post.tldr) ? post.tldr : [];

  return (
    <div
      className="relative block p-6 border-2 border-[#393A41] border-dashed rounded-2xl
    hover:border-red-400 transition-colors duration-200 group"
    >
      {/* Full-card hit target: must not wrap tag <a> links (invalid nested anchors). */}
      <TransitionLink
        href={`/blog/${post.slug}`}
        className="absolute inset-0 z-0 block rounded-[0.875rem] focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[#131316]"
        aria-label={`Read post: ${post.title}`}
      >
        <span className="sr-only">{post.title}</span>
      </TransitionLink>

      <div className="relative z-10 flex flex-col h-full pointer-events-none">
        {/* Header */}
        <h2
          className="text-lg font-bold text-white
          group-hover:text-red-400 transition-all group-hover:translate-x-1
          sm:text-xl md:text-2xl"
        >
          {post.title}
        </h2>

        {/* Tags + date — pointer-events-auto so tag links sit above the card <a> */}
        <div className="py-2 flex flex-row items-start justify-between mt-2">
          <div className="pointer-events-auto">
            <Tags tags={post.tags || []} linkable maxVisible={5} />
          </div>
          <div className="text-xs sm:text-sm text-[#808080]">
            {formatDate(post.published_at)}
          </div>
        </div>

        {/* TL;DR Section */}
        {tldrItems.length > 0 && (
          <div className="px-4">
            <p className="text-xs sm:text-sm font-bold text-[#808080] my-2">TL;DR</p>
            <ul className="space-y-2">
              {tldrItems.map((item, index) => {
                const displayText =
                  typeof item === "string"
                    ? item
                    : (item as { name: string }).name;

                return (
                  <li
                    key={index}
                    className="flex items-start text-white text-sm sm:text-base"
                  >
                    <span className="mr-2">•</span>
                    <span>{displayText}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Blog's Footer */}
        <div className="mt-6 flex items-center justify-between">
          {post.source_url && post.source_url.length > 0 && (
            <div className="text-xs sm:text-sm font-medium text-[#808080] inline-flex items-center flex-wrap pointer-events-auto">
              {post.source_url.length > 1 ? (
                <span className="mr-1">sources:</span>
              ) : (
                <span className="mr-1">source:</span>
              )}
              {post.source_url.map((source, index) => {
                const { name, url } = formatSource(source);

                return (
                  <span key={index} className="inline-flex items-center">
                    {index > 0 && <span className="mx-1">|</span>}
                    {url ? (
                      <button
                        type="button"
                        className="text-blue-400 hover:underline cursor-pointer group-hover:text-red-400 transition-colors"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          window.open(url, "_blank", "noopener,noreferrer");
                        }}
                      >
                        {name}
                      </button>
                    ) : (
                      <span className="text-blue-400 group-hover:text-red-400 transition-colors">
                        {name}
                      </span>
                    )}
                  </span>
                );
              })}
            </div>
          )}
          <span className="text-xs sm:text-sm font-medium text-blue-400 group-hover:text-red-400 group-hover:translate-x-1 transition-transform inline-flex items-center whitespace-nowrap">
            Read full post

            <div className="relative w-4 h-4 flex items-center justify-center">
              <ChevronRight
                size={16}
                className="absolute transition-all duration-300 group-hover:opacity-0 group-hover:translate-x-1"
              />
              <ArrowRight
                size={16}
                className="absolute opacity-0 group-hover:translate-x-1 transition-all duration-300 group-hover:opacity-100"
              />
            </div>
          </span>
        </div>
      </div>
    </div>
  );
}
