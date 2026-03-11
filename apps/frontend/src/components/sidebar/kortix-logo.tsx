'use client';

import { cn } from '@/lib/utils';

interface KortixLogoProps {
  size?: number;
  variant?: 'symbol' | 'logomark';
  className?: string;
}

export function KortixLogo({ size = 24, variant = 'symbol', className }: KortixLogoProps) {
  if (variant === 'logomark') {
    return (
      <>
        <img
          src="/ventureverse-logomark-light.svg"
          alt="VentureVerse"
          className={cn('dark:hidden flex-shrink-0', className)}
          style={{ height: `${size}px`, width: 'auto' }}
          suppressHydrationWarning
        />
        <img
          src="/ventureverse-logomark-dark.svg"
          alt="VentureVerse"
          className={cn('hidden dark:block flex-shrink-0', className)}
          style={{ height: `${size}px`, width: 'auto' }}
          suppressHydrationWarning
        />
      </>
    );
  }

  return (
    <img
      src="/ventureverse-symbol.svg"
      alt="VentureVerse"
      className={cn('flex-shrink-0', className)}
      style={{ width: `${size}px`, height: `${size}px` }}
      suppressHydrationWarning
    />
  );
}
