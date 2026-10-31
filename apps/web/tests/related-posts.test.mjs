import assert from 'node:assert/strict';
import { test } from 'node:test';
import { rankRelatedPosts } from '../src/lib/related-posts.ts';

const post = (id, tagIds, published_at = '2026-10-30T00:00:00Z', is_published = true) => ({
  id, slug: id, title: id, tldr: [], published_at, is_published,
  tags: tagIds.map(id => ({ id, name: String(id), slug: String(id) })),
});

test('ranks shared topics before recency, then returns at most three posts', () => {
  const candidates = [post('newer', [1], '2026-10-31T00:00:00Z'),
    post('best', [1, 2]), post('older', [2], '2026-10-29T00:00:00Z'),
    post('fourth', [1], '2026-10-28T00:00:00Z')];
  assert.deepEqual(rankRelatedPosts(candidates, 'current', [1, 2]).map(p => p.id),
    ['best', 'newer', 'older']);
});

test('excludes the current post, drafts and unrelated posts', () => {
  assert.deepEqual(rankRelatedPosts([post('current', [1]), post('draft', [1], undefined, false),
    post('unrelated', [3]), post('match', [1])], 'current', [1]).map(p => p.id), ['match']);
});

test('empty tags and empty candidate lists produce no recommendations', () => {
  assert.deepEqual(rankRelatedPosts([post('other', [1])], 'current', []), []);
  assert.deepEqual(rankRelatedPosts([], 'current', [1]), []);
});

test('duplicate tags do not inflate similarity and input order is not mutated', () => {
  const candidates = [post('duplicate', [1, 1, 1]), post('better', [1, 2])];
  assert.deepEqual(rankRelatedPosts(candidates, 'current', [1, 2]).map(p => p.id), ['better', 'duplicate']);
  assert.deepEqual(candidates.map(p => p.id), ['duplicate', 'better']);
});
