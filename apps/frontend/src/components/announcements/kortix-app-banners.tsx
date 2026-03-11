'use client';

import { useEffect, useState } from 'react';
import { Download, Laptop, X } from 'lucide-react';
import { motion } from 'framer-motion';
import { isElectron } from '@/lib/utils/is-electron';
import { KortixLogo } from '@/components/sidebar/kortix-logo';
import { MIRA_DESKTOP_ARM64_DMG_URL } from '@/lib/constants/app-downloads';

const DESKTOP_STORAGE_KEY = 'ventureverse-desktop-banner-dismissed';

type KortixAppBannersProps = {
  disableMobileAdvertising?: boolean;
};

export function KortixAppBanners(_props: KortixAppBannersProps) {
  const [mounted, setMounted] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setMounted(true);

    if (isElectron()) {
      return;
    }

    const dismissed = localStorage.getItem(DESKTOP_STORAGE_KEY);
    if (dismissed) {
      return;
    }

    const timer = window.setTimeout(() => setVisible(true), 1500);
    return () => window.clearTimeout(timer);
  }, []);

  const dismiss = () => {
    setVisible(false);
    localStorage.setItem(DESKTOP_STORAGE_KEY, 'true');
  };

  if (!mounted || !visible) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="fixed bottom-4 right-4 z-[100] w-[300px]"
    >
      <div className="relative overflow-hidden rounded-2xl border border-border/70 bg-white shadow-2xl dark:bg-[#161618] dark:border-[#232324]">
        <button
          onClick={dismiss}
          className="absolute right-3 top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-black/10 text-foreground transition-colors hover:bg-black/20 dark:bg-black/70 dark:text-white dark:hover:bg-black"
          aria-label="Dismiss desktop app banner"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-center justify-center bg-muted p-5 dark:bg-[#e8e4df]">
          <div className="flex h-16 w-[190px] items-center justify-center rounded-2xl border border-border/40 bg-background shadow-sm dark:border-transparent dark:bg-white">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white">
                <KortixLogo size={18} variant="symbol" />
              </div>
              <div className="text-left">
                <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Mira Desktop</div>
                <div className="text-sm font-semibold text-foreground">Mac (Apple Silicon)</div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-muted/40 p-4 dark:bg-[#111214]">
          <h3 className="text-sm font-semibold text-foreground dark:text-white">VentureVerse for Desktop</h3>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground dark:text-white/65">
            Download the latest Mira desktop build for Apple Silicon Macs. Mobile remains coming soon.
          </p>

          <a
            href={MIRA_DESKTOP_ARM64_DMG_URL}
            className="mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-black text-sm font-medium text-white transition-opacity hover:opacity-90 dark:bg-white dark:text-black"
          >
            <Download className="h-4 w-4" />
            Download DMG
          </a>

          <div className="mt-3 flex items-center gap-2 text-[11px] text-muted-foreground dark:text-white/50">
            <Laptop className="h-3.5 w-3.5" />
            Apple Silicon build only for now
          </div>
        </div>
      </div>
    </motion.div>
  );
}
