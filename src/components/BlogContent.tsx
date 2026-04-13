'use client';

import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Prism from 'prismjs';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-markup';
import 'prismjs/themes/prism-tomorrow.css';

interface BlogContentProps {
  content: string;
}

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

function sanitizeImageSrc(src?: string): string | null {
  if (!src) return null;

  try {
    const parsed = new URL(src);
    const protocol = parsed.protocol.toLowerCase();
    if (protocol === "http:" || protocol === "https:") {
      return src;
    }
    return null;
  } catch {
    return null;
  }
}

function getLanguageFromClassName(className?: string): string | null {
  if (!className) return null;
  const token = className
    .split(/\s+/)
    .find((part) => part.startsWith('language-'));
  if (!token) return null;
  const language = token.slice('language-'.length).trim().toLowerCase();
  return language || null;
}

function FencedCodeBlock({ language, code }: { language: string; code: string }) {
  const codeRef = useRef<HTMLElement>(null);
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');

  useEffect(() => {
    const el = codeRef.current;
    if (!el) return;
    el.textContent = code;
    Prism.highlightElement(el);
  }, [code, language]);

  useEffect(() => {
    if (copyState === 'idle') return;
    const timeout = window.setTimeout(() => setCopyState('idle'), 1200);
    return () => window.clearTimeout(timeout);
  }, [copyState]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopyState('copied');
    } catch {
      setCopyState('failed');
    }
  };

  return (
    <div className="relative group my-4">
      <div className="flex items-center justify-between bg-[#1a1a1a] border border-[#393A41] border-b-0 rounded-t-lg px-4 py-2">
        <span className="text-xs text-gray-400 font-mono">{language}</span>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={`Copy ${language} code block`}
          className="text-xs text-gray-500 hover:text-white transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 rounded px-1 py-0.5"
        >
          {copyState === 'copied' ? 'Copied' : copyState === 'failed' ? 'Failed' : 'Copy'}
        </button>
        <span className="sr-only" role="status" aria-live="polite">
          {copyState === 'copied' ? 'Code copied to clipboard' : copyState === 'failed' ? 'Failed to copy code to clipboard' : ''}
        </span>
      </div>
      <pre
        className={`language-${language} mt-0! rounded-t-none! rounded-b-lg! max-w-full min-w-0 whitespace-pre-wrap! wrap-anywhere px-4 py-3 text-sm`}
        suppressHydrationWarning
      >
        <code
          ref={codeRef}
          className={`language-${language} whitespace-pre-wrap! wrap-anywhere`}
          suppressHydrationWarning
        >
          {code}
        </code>
      </pre>
    </div>
  );
}

export default function BlogContent({ content }: BlogContentProps) {
  return (
    <article className="max-w-none text-white leading-relaxed space-y-4 mt-10 text-wrap">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre: ({ children }): ReactNode => children,
          p: ({ children }) => <p className="text-white text-wrap">{children}</p>,
          h1: ({ children }) => <h1 className="text-2xl font-bold text-white text-wrap mt-8 mb-4">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-bold text-white text-wrap mt-8 mb-4">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-bold text-white text-wrap mt-6 mb-3">{children}</h3>,
          h4: ({ children }) => <h4 className="text-base font-bold text-white mt-4 mb-2">{children}</h4>,
          h5: ({ children }) => <h5 className="text-sm font-bold text-white text-wrap mt-3 mb-2">{children}</h5>,
          h6: ({ children }) => <h6 className="text-sm font-semibold text-gray-200 text-wrap mt-3 mb-2">{children}</h6>,
          a: ({ href, children }) => {
            const safeHref = sanitizeLinkHref(href);
            if (!safeHref) {
              return <span className="text-gray-400 underline">{children}</span>;
            }
            const isExternal = safeHref.startsWith("http");
            return (
              <a
                href={safeHref}
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noopener noreferrer' : undefined}
                aria-label={isExternal ? `External link: ${safeHref} (opens in a new tab)` : undefined}
                className="text-blue-400 hover:text-blue-300 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 rounded-sm"
              >
                {children}
                {isExternal ? <span className="sr-only"> (opens in a new tab)</span> : null}
              </a>
            );
          },
          img: ({ src, alt }) => {
            const srcStr = typeof src === "string" ? src : undefined;
            const safe = srcStr ? sanitizeImageSrc(srcStr) : null;
            if (!safe) {
              return null;
            }
            return (
              <img
                src={safe}
                alt={typeof alt === "string" ? alt : ""}
                className="rounded-lg max-w-full h-auto my-6 border border-[#393A41]"
                loading="lazy"
                decoding="async"
              />
            );
          },
          ul: ({ children }) => <ul className="list-disc list-inside space-y-2 ml-4">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside space-y-2 ml-4">{children}</ol>,
          li: ({ children }) => <li className="text-white">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-[#6A6B70] pl-4 py-2 my-4 text-gray-300 italic">
              {children}
            </blockquote>
          ),
          code: ({ className, children }) => {
            const language = getLanguageFromClassName(className);
            const code = String(children).replace(/\n$/, '');

            if (!language) {
              return (
                <code className="bg-[#26262C] px-1.5 py-0.5 rounded text-sm font-mono text-pink-400">
                  {children}
                </code>
              );
            }

            return <FencedCodeBlock language={language} code={code} />;
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-6">
              <table className="min-w-full border border-[#393A41] rounded-lg overflow-hidden">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-[#1a1a1a]">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="bg-[#131316]">{children}</tbody>
          ),
          tr: ({ children }) => (
            <tr className="even:bg-[#1a1a1a]/50">{children}</tr>
          ),
          th: ({ children }) => (
            <th className="px-4 py-3 text-left text-sm font-bold text-white border-b border-[#393A41]">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-3 text-sm text-gray-300 border-b border-[#393A41]">
              {children}
            </td>
          ),
          hr: () => <hr className="border-[#393A41] my-8" />,
          strong: ({ children }) => <strong className="font-bold text-white">{children}</strong>,
          em: ({ children }) => <em className="italic text-gray-300">{children}</em>,
        }}
      >
        {content}
      </Markdown>
    </article>
  );
}
