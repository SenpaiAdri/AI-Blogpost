import Link from "next/link";
import { getRelatedPosts } from "@/lib/posts";
import { formatDate } from "@/lib/utils";
import type { Tag } from "@/lib/types";

export default async function RelatedPosts({ postId, tagIds }: { postId: string; tagIds: Tag['id'][] }) {
    const posts = await getRelatedPosts(postId, [...new Set(tagIds)].sort((a, b) => a - b));
    if (posts.length === 0) return null;

    return (
        <aside aria-labelledby="related-posts-heading" className="min-w-0 border-t border-dashed border-line pt-6 xl:border-t-0 xl:border-l-2 xl:border-line-strong xl:pl-6 xl:pt-0">
            <h2 id="related-posts-heading" className="text-lg font-bold text-ink-bright">Related articles</h2>
            <ul className="mt-4 divide-y divide-dashed divide-line">
                {posts.map(post => (
                    <li key={post.id} className="py-5 first:pt-0 last:pb-0">
                        <Link href={`/blog/${post.slug}`} className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface group">
                            <h3 className="text-base font-semibold leading-snug text-ink-bright group-hover:text-brand wrap-anywhere">{post.title}</h3>
                            {post.tldr?.[0] && <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-ink-body wrap-anywhere">{post.tldr[0]}</p>}
                            {post.published_at && <time dateTime={post.published_at} className="mt-3 block text-xs text-ink-muted">{formatDate(post.published_at)}</time>}
                        </Link>
                    </li>
                ))}
            </ul>
        </aside>
    );
}
