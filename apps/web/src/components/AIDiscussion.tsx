import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getApprovedComments } from "@/lib/posts";
import type { Comment } from "@/lib/types";
import { formatDate } from "@/lib/utils";

// Local copy of the BlogContent link guard: comment bodies are untrusted
// markdown, so only http/https/mailto (plus relative) links render as <a>.
// (Can't import it — BlogContent is a client component.)
function sanitizeLinkHref(href?: string): string | null {
  if (!href) return null;

  if (href.startsWith("/") || href.startsWith("#") || href.startsWith("?")) {
    return href;
  }

  try {
    const parsed = new URL(href);
    const protocol = parsed.protocol.toLowerCase();
    if (protocol === "http:" || protocol === "https:" || protocol === "mailto:") {
      return href;
    }
    return null;
  } catch {
    return null;
  }
}

function CommentBody({ body }: { body: string }) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="text-ink-strong text-sm sm:text-base text-wrap">{children}</p>,
        a: ({ href, children }) => {
          const safeHref = sanitizeLinkHref(href);
          if (!safeHref) {
            return <span className="text-ink-muted underline">{children}</span>;
          }
          const isExternal = safeHref.startsWith("http");
          return (
            <a
              href={safeHref}
              target={isExternal ? "_blank" : undefined}
              rel={isExternal ? "noopener noreferrer" : undefined}
              className="text-blue-400 hover:text-blue-300 underline"
            >
              {children}
            </a>
          );
        },
        img: () => null,
        h1: ({ children }) => <p className="font-bold text-ink-bright">{children}</p>,
        h2: ({ children }) => <p className="font-bold text-ink-bright">{children}</p>,
        h3: ({ children }) => <p className="font-bold text-ink-bright">{children}</p>,
        h4: ({ children }) => <p className="font-bold text-ink-bright">{children}</p>,
        h5: ({ children }) => <p className="font-bold text-ink-bright">{children}</p>,
        h6: ({ children }) => <p className="font-bold text-ink-bright">{children}</p>,
        ul: ({ children }) => <ul className="list-disc list-inside space-y-1 ml-4">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 ml-4">{children}</ol>,
        li: ({ children }) => <li className="text-ink-strong text-sm sm:text-base">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-line-strong pl-4 py-1 my-2 text-ink-body italic">
            {children}
          </blockquote>
        ),
        code: ({ children }) => (
          <code className="bg-surface px-1.5 py-0.5 rounded text-sm font-mono text-pink-400">
            {children}
          </code>
        ),
        pre: ({ children }) => <pre className="whitespace-pre-wrap wrap-anywhere">{children}</pre>,
        strong: ({ children }) => <strong className="font-bold text-ink-bright">{children}</strong>,
        em: ({ children }) => <em className="italic text-ink-body">{children}</em>,
      }}
    >
      {body}
    </Markdown>
  );
}

function CommentCard({ comment }: { comment: Comment }) {
  const name = comment.author_name || "Critic AI";
  const isAI = comment.author_type === "ai";

  return (
    <article className="rounded-2xl bg-surface-3 border border-line border-dashed p-5 space-y-3">
      <header className="flex flex-wrap items-center gap-2">
        <span
          aria-hidden
          className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500/15 text-blue-300 text-xs font-bold"
        >
          {isAI ? "AI" : name.slice(0, 1).toUpperCase()}
        </span>
        <span className="text-sm font-semibold text-ink-bright">{name}</span>
        {isAI && (
          <span className="rounded-4xl bg-blue-500/10 px-2.5 py-0.5 text-xs font-semibold text-blue-300">
            AI Comment
          </span>
        )}
        {comment.ai_model && (
          <span className="text-xs text-ink-faint" title={comment.ai_model}>
            {comment.ai_model.split("/").pop()}
          </span>
        )}
        <span className="text-xs text-ink-faint ml-auto">
          {formatDate(comment.created_at)}
        </span>
      </header>
      <div className="space-y-2">
        <CommentBody body={comment.body} />
      </div>
    </article>
  );
}

export function AIDiscussionSkeleton() {
  return (
    <div className="pt-8 border-t border-line mt-12 animate-pulse" aria-hidden>
      <div className="h-5 w-32 rounded bg-surface-3 mb-4" />
      <div className="rounded-2xl bg-surface-3 p-5 space-y-3">
        <div className="h-4 w-48 rounded bg-line" />
        <div className="h-4 w-full rounded bg-line" />
        <div className="h-4 w-5/6 rounded bg-line" />
      </div>
    </div>
  );
}

export default async function AIDiscussion({ postId }: { postId: string }) {
  const comments = await getApprovedComments(postId);

  // Zero comments is a valid outcome (selective pipeline) — render nothing.
  if (comments.length === 0) {
    return null;
  }

  return (
    <section aria-label="AI Discussion" className="pt-8 border-t border-line mt-12 space-y-4">
      <div>
        <h2 className="text-sm font-bold text-ink-muted">
          AI Discussion{comments.length > 1 ? ` (${comments.length})` : ""}
        </h2>
        <p className="text-xs text-ink-faint mt-1">
          What our AI discussant flagged about this post.
        </p>
      </div>
      {comments.map((comment) => (
        <CommentCard key={comment.id} comment={comment} />
      ))}
    </section>
  );
}
