"use client";

import { useState, useRef, useEffect } from "react";
import { Share2, Link, Check } from "lucide-react";

interface ShareButtonProps {
  slug: string;
}

export default function ShareButton({ slug }: ShareButtonProps) {
  const [copied, setCopied] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleCopyLink = () => {
    const origin = typeof window !== "undefined" && window.location.origin ? window.location.origin : "";
    const url = `${origin}/blog/${slug}`;

    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => {
        setCopied(false);
        setIsOpen(false);
      }, 2000);
    });
  };

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-2 py-1.5 text-gray-400 hover:text-white transition-colors"
      >
        <Share2 size={16} />
      </button>

      {isOpen && (
        <div className="group absolute right-0 mt-2 bg-[#131316] border-2 border-[#6A6B70] hover:border-red-500 border-dashed rounded-xl shadow-4xl z-10 p-1">
          <button
            onClick={handleCopyLink}
            className="w-full text-left px-3 py-2 text-sm text-gray-300 group-hover:text-red-500 flex items-center justify-between transition-colors"
          >
            <div className="flex items-center gap-2">
              <Link size={14} />
              <span className="text-sm text-nowrap">Copy Link</span>
            </div>
            {copied && <Check size={14} className="ml-2 text-green-400" />}
          </button>
        </div>
      )}
    </div>
  );
}