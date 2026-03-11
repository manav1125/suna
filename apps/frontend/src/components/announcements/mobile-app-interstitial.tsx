'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Clock3, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { KortixLogo } from '@/components/sidebar/kortix-logo';

const STORAGE_KEY = 'ventureverse-mobile-banner-dismissed';
const DISMISS_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000;

function isMobileDevice(): boolean {
  if (typeof window === 'undefined') return false;
  return /iphone|ipad|ipod|android/i.test(window.navigator.userAgent);
}

function wasDismissedRecently(): boolean {
  if (typeof window === 'undefined') return false;
  const dismissedAt = localStorage.getItem(STORAGE_KEY);
  if (!dismissedAt) return false;
  return Date.now() - parseInt(dismissedAt, 10) < DISMISS_EXPIRY_MS;
}

export function MobileAppInterstitial() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (!isMobileDevice() || wasDismissedRecently()) {
      return;
    }

    const timer = window.setTimeout(() => setIsVisible(true), 1500);
    return () => window.clearTimeout(timer);
  }, []);

  const dismiss = () => {
    setIsVisible(false);
    localStorage.setItem(STORAGE_KEY, Date.now().toString());
  };

  if (!isVisible) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: 120, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 120, opacity: 0 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className="fixed bottom-0 left-0 right-0 z-[100] p-4"
        style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}
      >
        <div className="relative mx-auto max-w-lg overflow-hidden rounded-2xl border border-border bg-background/95 shadow-xl backdrop-blur-md">
          <button
            onClick={dismiss}
            className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-muted/80 transition-colors hover:bg-muted"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>

          <div className="flex items-start gap-4 p-5 pr-12">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-sm">
              <KortixLogo size={22} variant="symbol" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                <Clock3 className="h-3.5 w-3.5" />
                Mobile Coming Soon
              </div>
              <h3 className="mt-2 text-base font-semibold text-foreground">VentureVerse mobile is not live yet</h3>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                Use the web app for now, or open the desktop download page from a Mac to install the Mira desktop app.
              </p>

              <Link
                href="/app"
                className="mt-4 inline-flex h-10 items-center justify-center rounded-xl border border-border px-4 text-sm font-medium text-foreground hover:bg-accent"
              >
                Learn about the desktop app
              </Link>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
