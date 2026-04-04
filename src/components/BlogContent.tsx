'use client';

import Markdown from 'react-markdown';
import Prism from 'prismjs';
import { useEffect, useState } from 'react';
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

export default function BlogContent({ content }: BlogContentProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    Prism.highlightAll();
  }, [content]);

  return (
    <article className="max-w-none text-white leading-relaxed space-y-4 mt-10 text-wrap">
      <Markdown
        components={{
          p: ({ children }) => <p className="text-white text-wrap">{children}</p>,
          h1: ({ children }) => <h1 className="text-2xl font-bold text-white text-wrap mt-8 mb-4">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-bold text-white text-wrap mt-8 mb-4">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-bold text-white text-wrap mt-6 mb-3">{children}</h3>,
          h4: ({ children }) => <h4 className="text-base font-bold text-white mt-4 mb-2">{children}</h4>,
          h5: ({ children }) => <h5 className="text-sm font-bold text-white text-wrap mt-3 mb-2">{children}</h5>,
          a: ({ href, children }) => {
            const isExternal = href?.startsWith('http');
            return (
              <a
                href={href}
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noopener noreferrer' : undefined}
                className="text-blue-400 hover:text-blue-300 underline"
              >
                {children}
              </a>
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
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : 'text';
            const code = String(children).replace(/\n$/, '');

            if (!match) {
              return (
                <code className="bg-[#26262C] px-1.5 py-0.5 rounded text-sm font-mono text-pink-400">
                  {children}
                </code>
              );
            }

            useEffect(() => {
              if (mounted) {
                Prism.highlightAll();
              }
            }, [code, language]);

            return (
              <div className="relative group my-4">
                <div className="flex items-center justify-between bg-[#1a1a1a] border border-[#393A41] border-b-0 rounded-t-lg px-4 py-2">
                  <span className="text-xs text-gray-400 font-mono">{language}</span>
                  <button
                    onClick={() => navigator.clipboard.writeText(code)}
                    className="text-xs text-gray-500 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
                  >
                    Copy
                  </button>
                </div>
                <pre className={`language-${language} !mt-0 !rounded-t-none !rounded-b-lg overflow-x-auto`}>
                  <code className={`language-${language}`}>{code}</code>
                </pre>
              </div>
            );
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
