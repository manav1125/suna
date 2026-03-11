'use client';

import Image from 'next/image';
import Link from 'next/link';
import {
  ArrowUpRight,
  Clock3,
  Download,
  Laptop,
  ShieldCheck,
  Smartphone,
  Sparkles,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { SimpleFooter } from '@/components/home/simple-footer';
import {
  MIRA_DESKTOP_ARM64_DMG_URL,
  MIRA_DESKTOP_RELEASE_URL,
} from '@/lib/constants/app-downloads';

const DESKTOP_FEATURES = [
  {
    icon: Sparkles,
    title: 'Native handoff workflow',
    description:
      'Open Mira from your Mac, hand off work instantly, and keep the same venture context across every session.',
  },
  {
    icon: Laptop,
    title: 'Built for Apple Silicon',
    description:
      'This current desktop build is tuned for modern M-series Macs and distributed as a direct DMG download.',
  },
  {
    icon: ShieldCheck,
    title: 'Private by default',
    description:
      'Use the desktop app for a tighter local workflow while your account, auth, and cloud state stay in sync.',
  },
];

export default function AppDownloadPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-20 px-6 py-16 md:px-10 md:py-20">
        <section className="grid gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="max-w-2xl"
          >
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/60 px-3 py-1.5 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              <Laptop className="h-3.5 w-3.5" />
              Desktop App
            </div>

            <h1 className="text-4xl font-semibold tracking-tight text-foreground md:text-6xl">
              VentureVerse for Desktop
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground md:text-lg">
              Download the Mira desktop app for Apple Silicon Macs and run your venture workflows in a faster,
              cleaner native workspace. Mobile is in progress and coming soon.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <a
                href={MIRA_DESKTOP_ARM64_DMG_URL}
                className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-foreground px-5 text-sm font-medium text-background hover:bg-foreground/90"
              >
                <Download className="h-4 w-4" />
                Download for Mac (Apple Silicon)
              </a>
              <a
                href={MIRA_DESKTOP_RELEASE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-12 items-center justify-center gap-2 rounded-xl border border-border bg-background px-5 text-sm font-medium text-foreground hover:bg-accent"
              >
                View Release
                <ArrowUpRight className="h-4 w-4" />
              </a>
            </div>

            <div className="mt-4 text-sm text-muted-foreground">
              Current build: Mira by Venture Verse 1.0.0 for Apple Silicon
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="rounded-[28px] border border-border/70 bg-card/40 p-4 shadow-[0_24px_80px_-40px_rgba(0,0,0,0.55)]"
          >
            <div className="overflow-hidden rounded-[22px] border border-border/60 bg-[#0d0f13]">
              <div className="border-b border-white/10 px-5 py-3 text-xs font-medium uppercase tracking-[0.16em] text-white/55">
                Mira Computer
              </div>
              <div className="relative aspect-[16/10]">
                <Image
                  src="/mira-computer-dark.svg"
                  alt="Mira desktop app preview"
                  fill
                  className="object-cover"
                  priority
                />
              </div>
            </div>
          </motion.div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {DESKTOP_FEATURES.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.15 + index * 0.08 }}
              className="rounded-2xl border border-border/70 bg-card/40 p-6"
            >
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-foreground/6">
                <feature.icon className="h-5 w-5 text-foreground" />
              </div>
              <h2 className="text-lg font-semibold text-foreground">{feature.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{feature.description}</p>
            </motion.div>
          ))}
        </section>

        <section className="grid gap-6 rounded-3xl border border-border/70 bg-card/30 p-8 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-foreground/6 px-3 py-1.5 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
              <Smartphone className="h-3.5 w-3.5" />
              Mobile Coming Soon
            </div>
            <h2 className="text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
              Mobile is next, but not live yet
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground md:text-base">
              We are not publishing iOS or Android downloads yet. For now, use VentureVerse in the browser or on the
              desktop app, and we&apos;ll announce the mobile launch once it is ready.
            </p>
          </div>

          <div className="rounded-2xl border border-border/70 bg-background/80 px-5 py-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2 font-medium text-foreground">
              <Clock3 className="h-4 w-4" />
              Current availability
            </div>
            <div className="mt-2">Desktop: live for Apple Silicon Macs</div>
            <div className="mt-1">Mobile: coming soon</div>
          </div>
        </section>

        <section className="rounded-3xl border border-border/70 bg-card/20 p-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-foreground">Need the browser version instead?</h2>
              <p className="mt-2 text-sm text-muted-foreground md:text-base">
                You can keep using the full web app while we expand platform coverage.
              </p>
            </div>
            <Link
              href="/auth"
              className="inline-flex h-12 items-center justify-center rounded-xl border border-border bg-background px-5 text-sm font-medium text-foreground hover:bg-accent"
            >
              Open VentureVerse Web
            </Link>
          </div>
        </section>
      </div>

      <SimpleFooter />
    </main>
  );
}
