"use client";

import Link, { type LinkProps } from "next/link";
import { useRouter } from "next/navigation";
import {
  type AnchorHTMLAttributes,
  type MouseEvent,
  type ReactNode,
  useCallback,
} from "react";
import { usePageTransition } from "./PageTransitionProvider";

type TransitionLinkProps = Omit<LinkProps, "href" | "onClick"> &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href" | "onClick"> & {
    href: string;
    children: ReactNode;
    disableTransition?: boolean;
    onClick?: AnchorHTMLAttributes<HTMLAnchorElement>["onClick"];
  };

function isModifiedClick(event: MouseEvent<HTMLAnchorElement>) {
  return event.metaKey || event.ctrlKey || event.shiftKey || event.altKey;
}

function toAbsoluteUrl(href: string) {
  try {
    return new URL(href, window.location.href);
  } catch {
    return null;
  }
}

function toRouterHref(href: string) {
  const url = toAbsoluteUrl(href);
  if (!url) return href;
  return `${url.pathname}${url.search}${url.hash}`;
}

type LenisLike = {
  scrollTo: (target: string | number | Element, options?: { immediate?: boolean }) => void;
};

function getLenisInstance() {
  const maybeLenis = (
    window as Window & { lenis?: Partial<LenisLike> | undefined }
  ).lenis;

  if (!maybeLenis || typeof maybeLenis.scrollTo !== "function") {
    return null;
  }

  return maybeLenis as LenisLike;
}

function scrollToHash(hash: string) {
  const targetId = decodeURIComponent(hash.replace(/^#/, ""));
  if (!targetId) return;

  const targetElement = document.getElementById(targetId);
  if (!targetElement) return;

  const lenis = getLenisInstance();
  if (lenis) {
    lenis.scrollTo(targetElement);
    return;
  }

  targetElement.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function TransitionLink({
  href,
  children,
  disableTransition = false,
  onClick,
  target,
  download,
  ...rest
}: TransitionLinkProps) {
  const router = useRouter();
  const { triggerTransition } = usePageTransition();

  const handleClick = useCallback(
    (event: MouseEvent<HTMLAnchorElement>) => {
      onClick?.(event);
      if (event.defaultPrevented) return;

      if (
        disableTransition ||
        event.button !== 0 ||
        isModifiedClick(event) ||
        target === "_blank" ||
        Boolean(download)
      ) {
        return;
      }

      const targetUrl = toAbsoluteUrl(href);
      if (!targetUrl) return;

      const currentUrl = new URL(window.location.href);

      if (targetUrl.origin !== currentUrl.origin) return;

      const isSamePathAndQuery =
        targetUrl.pathname === currentUrl.pathname &&
        targetUrl.search === currentUrl.search;

      if (isSamePathAndQuery && targetUrl.hash) {
        event.preventDefault();
        scrollToHash(targetUrl.hash);
        return;
      }

      if (
        targetUrl.pathname === currentUrl.pathname &&
        targetUrl.search === currentUrl.search &&
        targetUrl.hash === currentUrl.hash
      ) {
        return;
      }

      event.preventDefault();
      triggerTransition(() => {
        router.push(toRouterHref(targetUrl.href));
      });
    },
    [disableTransition, download, href, onClick, router, target, triggerTransition]
  );

  return (
    <Link
      href={href}
      onClick={handleClick}
      target={target}
      download={download}
      data-no-transition={disableTransition ? "true" : undefined}
      {...rest}
    >
      {children}
    </Link>
  );
}
