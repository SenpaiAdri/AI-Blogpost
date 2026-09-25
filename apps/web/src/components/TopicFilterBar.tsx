"use client";

import type { TagWithCount } from "@/lib/posts";
import { useMemo, useState } from "react";
import TransitionLink from "./TransitionLink";

/** Max topic chips before "Show more" (sorted by popularity on the server). */
const TOPIC_PREVIEW_LIMIT = 5;

type Props = {
  tags: TagWithCount[];
  activeSlug?: string | null;
  tagQueryInvalid?: boolean;
};

export default function TopicFilterBar({
  tags,
  activeSlug,
  tagQueryInvalid,
}: Props) {
  const [expanded, setExpanded] = useState(false);

  const displayTags = useMemo(() => {
    if (expanded || tags.length <= TOPIC_PREVIEW_LIMIT) {
      return tags;
    }
    let slice = tags.slice(0, TOPIC_PREVIEW_LIMIT);
    if (activeSlug) {
      const active = tags.find((t) => t.tag.slug === activeSlug);
      if (active && !slice.some((t) => t.tag.slug === activeSlug)) {
        slice = [...tags.slice(0, TOPIC_PREVIEW_LIMIT - 1), active];
      }
    }
    return slice;
  }, [tags, expanded, activeSlug]);

  const canToggle = tags.length > TOPIC_PREVIEW_LIMIT;

  if (!tags.length && !tagQueryInvalid) {
    return null;
  }

  return (
    <div className="space-y-3 pb-2">
      {tagQueryInvalid && (
        <p className="text-sm text-amber-400/90 px-1">
          That topic wasn&apos;t found. Showing all posts.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-ink-faint shrink-0">
          Topics
        </span>
        <TransitionLink
          href="/"
          className={`text-xs font-semibold uppercase tracking-wide px-3 py-1.5 rounded-full border border-dashed transition-colors ${!activeSlug
            ? "border-brand text-brand bg-brand/10"
            : "border-line text-ink-body hover:border-line-strong hover:text-ink-bright"
            }`}
        >
          All
        </TransitionLink>
        {displayTags.map(({ tag, count }) => {
          const isActive = activeSlug === tag.slug;
          return (
            <TransitionLink
              key={String(tag.id)}
              href={`/?tag=${encodeURIComponent(tag.slug)}`}
              className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${isActive
                ? "border-brand text-brand bg-brand/10"
                : "border-line text-ink-strong bg-surface-3 hover:border-brand/60"
                }`}
            >
              {tag.name}
              <span className="ml-1 text-ink-faint tabular-nums">{count}</span>
            </TransitionLink>
          );
        })}
        {canToggle && !expanded && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="text-xs font-semibold px-3 py-1.5 rounded-full border border-dashed border-line text-ink-body hover:border-line-strong hover:text-brand transition-colors uppercase tracking-wide"
          >
            +{tags.length - displayTags.length} more
          </button>
        )}
        {canToggle && expanded && (
          <button
            type="button"
            onClick={() => setExpanded(false)}
            className="text-xs font-semibold px-3 py-1.5 rounded-full border border-dashed border-line text-ink-body hover:border-line-strong hover:text-ink-bright transition-colors uppercase tracking-wide"
          >
            Show less
          </button>
        )}
        <TransitionLink
          href="/topics"
          className="text-xs font-semibold text-ink-faint hover:text-brand transition-colors ml-1 uppercase tracking-wide"
        >
          All topics →
        </TransitionLink>
      </div>
    </div>
  );
}
