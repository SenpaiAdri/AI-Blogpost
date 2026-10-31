import type { Post, Tag } from './types';

export type RelatedPost = Pick<Post, 'id' | 'slug' | 'title' | 'tldr' | 'published_at' | 'is_published' | 'tags'>;

export function rankRelatedPosts(
    candidates: RelatedPost[],
    currentPostId: string,
    tagIds: Tag['id'][]
): RelatedPost[] {
    const currentTags = new Set(tagIds);
    return candidates
        .filter(post => post.id !== currentPostId && post.is_published)
        .map(post => ({
            post,
            overlap: new Set(post.tags?.filter(tag => currentTags.has(tag.id)).map(tag => tag.id)).size,
        }))
        .filter(({ overlap }) => overlap > 0)
        .sort((a, b) => b.overlap - a.overlap
            || (b.post.published_at ?? '').localeCompare(a.post.published_at ?? '')
            || a.post.id.localeCompare(b.post.id))
        .slice(0, 3)
        .map(({ post }) => post);
}
