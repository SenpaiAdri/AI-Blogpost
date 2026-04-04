'use client';

import React, { useState } from 'react';
import Prism from 'prismjs';
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

interface CodeBlockProps {
  children: string;
  className?: string;
}

export default function CodeBlock({ children, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const language = className?.replace(/language-/, '') || 'text';
  const code = children?.trim() || '';

  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      Prism.highlightAll();
    }
  }, [code, language]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const languageLabel = language.charAt(0).toUpperCase() + language.slice(1);

  return (
    <div className="relative group my-4">
      <div className="flex items-center justify-between bg-[#1a1a1a] border border-[#393A41] rounded-t-lg px-4 py-2">
        <span className="text-xs text-gray-400 font-mono">{languageLabel}</span>
        <button
          onClick={handleCopy}
          className="text-xs text-gray-500 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className={`language-${language} !mt-0 !rounded-t-none`}>
        <code className={`language-${language}`}>{code}</code>
      </pre>
    </div>
  );
}
