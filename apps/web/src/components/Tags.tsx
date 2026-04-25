"use client";

import { Tag } from "@/lib/types";
import { useState } from "react";
import TransitionLink from "./TransitionLink";

const chipClass =
  "text-xs font-medium text-[#E7E7E7] bg-[#2c2c31] border border-[#3e3e44] px-2.5 py-1 rounded-full whitespace-nowrap";

export default function Tags({
  tags,
  linkable = false,
  maxVisible,
}: {
  tags: Tag[];
  linkable?: boolean;
  /** When set, collapses long tag lists with a “+N more” control. */
  maxVisible?: number;
}) {
  const [showAll, setShowAll] = useState(false);

  if (!tags?.length) return null;

  const limit =
    maxVisible != null && maxVisible > 0 ? maxVisible : tags.length;
  const overflow = tags.length > limit && !showAll;
  const visible = overflow ? tags.slice(0, limit) : tags;
  const rest = tags.length - limit;

  return (
    <div className="flex flex-wrap sm:gap-4 gap-2 items-center">
      {visible.map((tag: Tag) =>
        linkable ? (
          <TransitionLink
            key={String(tag.id)}
            href={`/?tag=${encodeURIComponent(tag.slug)}`}
            onClick={(e) => e.stopPropagation()}
            className={`${chipClass} hover:border-red-400/50 hover:text-red-300 transition-colors`}
          >
            {tag.name}
          </TransitionLink>
        ) : (
          <span key={String(tag.id)} className={chipClass}>
            {tag.name}
          </span>
        )
      )}
      {overflow && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setShowAll(true);
          }}
          className={`${chipClass} text-[#9A9BA2] border-dashed hover:border-red-400/50 hover:text-red-300 cursor-pointer`}
        >
          +{rest} more
        </button>
      )}
    </div>
  );
}
