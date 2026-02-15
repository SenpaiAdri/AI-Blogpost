"use client";

import {
  type AnimationEvent,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

type TransitionState = "idle" | "covering" | "revealing";
type TransitionCallback = () => void;

interface PageTransitionContextType {
  triggerTransition: (callback: TransitionCallback) => boolean;
}

const PageTransitionContext = createContext<PageTransitionContextType>({
  triggerTransition: () => false,
});

const STRIP_STAGGER_MS = 100;
const STRIP_COUNT = 3;
const NAVIGATION_FALLBACK_MS = 1200;
const STRIP_INDEXES = Array.from({ length: STRIP_COUNT }, (_, index) => index);

export function usePageTransition() {
  return useContext(PageTransitionContext);
}

function isModifiedClick(event: MouseEvent) {
  return event.metaKey || event.ctrlKey || event.shiftKey || event.altKey;
}

function getAnchorFromEventTarget(target: EventTarget | null) {
  if (!(target instanceof Element)) return null;
  const anchor = target.closest("a[href]");
  return anchor instanceof HTMLAnchorElement ? anchor : null;
}

function toAbsoluteUrl(href: string) {
  try {
    return new URL(href, window.location.href);
  } catch {
    return null;
  }
}

function toRouteKey(url: URL) {
  return `${url.pathname}${url.search}`;
}

function toRouterHref(url: URL) {
  return `${url.pathname}${url.search}${url.hash}`;
}

export default function PageTransitionProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const routeKey = useMemo(() => {
    const query = searchParams.toString();
    return query ? `${pathname}?${query}` : pathname;
  }, [pathname, searchParams]);

  const [state, setState] = useState<TransitionState>("idle");
  const stateRef = useRef<TransitionState>("idle");
  const callbackRef = useRef<TransitionCallback | null>(null);
  const waitingForRouteRef = useRef(false);
  const fallbackTimerRef = useRef<number | null>(null);

  const setTransitionState = useCallback((nextState: TransitionState) => {
    stateRef.current = nextState;
    setState(nextState);
  }, []);

  useEffect(() => {
    if (waitingForRouteRef.current && stateRef.current === "covering") {
      waitingForRouteRef.current = false;
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
      const frame = window.requestAnimationFrame(() => {
        setTransitionState("revealing");
      });

      return () => {
        window.cancelAnimationFrame(frame);
      };
    }
  }, [routeKey, setTransitionState]);

  useEffect(() => {
    return () => {
      if (fallbackTimerRef.current !== null) {
        window.clearTimeout(fallbackTimerRef.current);
      }
    };
  }, []);

  const triggerTransition = useCallback(
    (callback: TransitionCallback) => {
      if (stateRef.current !== "idle") return false;

      callbackRef.current = callback;
      waitingForRouteRef.current = true;
      setTransitionState("covering");
      return true;
    },
    [setTransitionState]
  );

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent) => {
      if (event.defaultPrevented) return;
      if (event.button !== 0 || isModifiedClick(event)) return;
      if (stateRef.current !== "idle") return;

      const anchor = getAnchorFromEventTarget(event.target);
      if (!anchor) return;

      if (
        anchor.dataset.noTransition === "true" ||
        anchor.target === "_blank" ||
        anchor.hasAttribute("download")
      ) {
        return;
      }

      const rawHref = anchor.getAttribute("href");
      if (!rawHref) return;

      const targetUrl = toAbsoluteUrl(rawHref);
      if (!targetUrl) return;

      const currentUrl = new URL(window.location.href);
      if (targetUrl.origin !== currentUrl.origin) return;

      // Same route navigations (including hash-only changes) should remain native.
      if (toRouteKey(targetUrl) === routeKey) return;

      event.preventDefault();
      triggerTransition(() => {
        router.push(toRouterHref(targetUrl));
      });
    };

    document.addEventListener("click", handleDocumentClick);
    return () => {
      document.removeEventListener("click", handleDocumentClick);
    };
  }, [routeKey, router, triggerTransition]);

  const handleStripAnimationEnd = useCallback(
    (event: AnimationEvent<HTMLDivElement>) => {
      if (event.currentTarget !== event.target) return;

      if (stateRef.current === "covering") {
        if (fallbackTimerRef.current !== null) {
          window.clearTimeout(fallbackTimerRef.current);
          fallbackTimerRef.current = null;
        }

        const transitionCallback = callbackRef.current;
        callbackRef.current = null;
        transitionCallback?.();

        // Keep the app from staying covered forever if navigation is blocked.
        fallbackTimerRef.current = window.setTimeout(() => {
          if (stateRef.current === "covering") {
            waitingForRouteRef.current = false;
            setTransitionState("revealing");
          }
        }, NAVIGATION_FALLBACK_MS);

        return;
      }

      if (stateRef.current === "revealing") {
        if (fallbackTimerRef.current !== null) {
          window.clearTimeout(fallbackTimerRef.current);
          fallbackTimerRef.current = null;
        }
        waitingForRouteRef.current = false;
        setTransitionState("idle");
      }
    },
    [setTransitionState]
  );

  return (
    <PageTransitionContext.Provider value={{ triggerTransition }}>
      {state !== "idle" && (
        <div className="page-transition-overlay" aria-hidden="true">
          {STRIP_INDEXES.map((index) => (
            <div
              key={index}
              className={`page-transition-strip page-transition-strip--${index} page-transition-strip--${state}`}
              style={{ animationDelay: `${index * STRIP_STAGGER_MS}ms` }}
              onAnimationEnd={
                index === STRIP_COUNT - 1 ? handleStripAnimationEnd : undefined
              }
            />
          ))}
        </div>
      )}
      {children}
    </PageTransitionContext.Provider>
  );
}
