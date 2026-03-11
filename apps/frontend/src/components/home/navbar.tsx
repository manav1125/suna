'use client';

import { ThemeToggle } from '@/components/home/theme-toggle';
import { siteConfig } from '@/lib/site-config';
import { cn } from '@/lib/utils';
import { X, Menu } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import Link from 'next/link';
import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@/components/AuthProvider';
import { useRouter, usePathname } from 'next/navigation';
import { KortixLogo } from '@/components/sidebar/kortix-logo';
import { useTranslations } from 'next-intl';
import { trackCtaSignup } from '@/lib/analytics/gtm';
import { isMobileDevice } from '@/lib/utils/is-mobile-device';

// Scroll threshold with hysteresis to prevent flickering
const SCROLL_THRESHOLD_DOWN = 50;
const SCROLL_THRESHOLD_UP = 20;

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

const drawerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      duration: 0.2,
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
  exit: {
    opacity: 0,
    transition: { duration: 0.15 },
  },
};

const drawerMenuContainerVariants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
    },
  },
};

const drawerMenuVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { 
    opacity: 1, 
    x: 0,
    transition: {
      duration: 0.3,
      ease: "easeOut" as const,
    },
  },
};

interface NavbarProps {
  isAbsolute?: boolean;
}

export function Navbar({ isAbsolute = false }: NavbarProps) {
  const [hasScrolled, setHasScrolled] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('hero');
  const [isMobile, setIsMobile] = useState(false);
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations('common');
  const lastScrollY = useRef(0);

  const filteredNavLinks = siteConfig.nav.links;

  // Detect if user is on an actual mobile device (iOS/Android)
  useEffect(() => {
    setIsMobile(isMobileDevice());
  }, []);

  // Mobile users are sent to the app landing page, desktop users go straight to auth.
  const ctaLink = isMobile ? '/app' : '/auth';

  // Single unified scroll handler with hysteresis
  const handleScroll = useCallback(() => {
    const currentScrollY = window.scrollY;
    
    // Hysteresis: different thresholds for scrolling up vs down
    if (!hasScrolled && currentScrollY > SCROLL_THRESHOLD_DOWN) {
      setHasScrolled(true);
    } else if (hasScrolled && currentScrollY < SCROLL_THRESHOLD_UP) {
      setHasScrolled(false);
    }

    // Update active section
    const sections = filteredNavLinks.map((item) => item.href.substring(1));
    for (const section of sections) {
      const element = document.getElementById(section);
      if (element) {
        const rect = element.getBoundingClientRect();
        if (rect.top <= 150 && rect.bottom >= 150) {
          setActiveSection(section);
          break;
        }
      }
    }

    lastScrollY.current = currentScrollY;
  }, [hasScrolled, filteredNavLinks]);

  useEffect(() => {
    // Use passive listener for better scroll performance
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Initial check
    return () => window.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  const toggleDrawer = () => setIsDrawerOpen((prev) => !prev);
  const handleOverlayClick = () => setIsDrawerOpen(false);

  return (
    <header className={cn(
      "flex justify-center px-6 md:px-0 pt-4",
      isAbsolute ? "" : "sticky top-0 z-50"
    )}>
      <div className="w-full max-w-4xl">
        <div className="mx-auto rounded-2xl md:px-6 bg-transparent">
          <div className="relative flex h-[56px] items-center py-2 md:p-4">
            {/* Left Section - Logo */}
            <div className="flex items-center justify-start flex-shrink-0">
              <Link href="/" className="flex items-center gap-3">
                <KortixLogo size={18} variant='logomark' />
              </Link>
            </div>

            {/* Center Section - Nav Links (absolutely centered) */}
            <nav className="hidden md:flex items-center justify-center gap-1 absolute left-1/2 -translate-x-1/2">
              {filteredNavLinks.map((item) => (
                <Link
                  key={item.id}
                  href={item.href}
                  className={cn(
                    "px-3 py-1.5 text-sm font-medium rounded-lg transition-colors",
                    pathname === item.href
                      ? "text-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {item.name}
                </Link>
              ))}
              
              <Link
                href="/app"
                className={cn(
                  "px-3 py-1.5 text-sm font-medium rounded-lg transition-colors",
                  pathname === '/app'
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                App
              </Link>
            </nav>

            {/* Right Section - Actions */}
            <div className="flex items-center justify-end gap-2 sm:gap-3 ml-auto">
              {user ? (
                <Link
                  href="/dashboard"
                  className="h-8 px-4 text-sm font-medium rounded-lg bg-foreground text-background hover:bg-foreground/90 transition-colors inline-flex items-center justify-center"
                >
                  Dashboard
                </Link>
              ) : (
                <Link
                  href={ctaLink}
                  onClick={() => trackCtaSignup()}
                  className="h-8 px-4 text-sm font-medium rounded-lg bg-foreground text-background hover:bg-foreground/90 transition-colors inline-flex items-center justify-center"
                  suppressHydrationWarning
                >
                  {t('tryFree')}
                </Link>
              )}
              
              {/* Mobile Menu Button */}
              <button
                onClick={toggleDrawer}
                className="md:hidden p-2 rounded-lg hover:bg-accent transition-colors"
                aria-label="Open menu"
              >
                <Menu className="size-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Drawer - Full Screen */}
      <AnimatePresence>
        {isDrawerOpen && (
          <motion.div
            className="fixed inset-0 bg-background z-50 flex flex-col pt-4"
            initial="hidden"
            animate="visible"
            exit="exit"
            variants={drawerVariants}
          >
            {/* Header - matches navbar positioning */}
            <div className="flex h-[56px] items-center justify-between px-6 py-2">
              <Link href="/" className="flex items-center gap-3" onClick={() => setIsDrawerOpen(false)}>
                <KortixLogo size={18} variant='logomark' />
              </Link>
              <button
                onClick={toggleDrawer}
                className="border border-border rounded-lg p-2 cursor-pointer hover:bg-accent transition-colors"
                aria-label="Close menu"
              >
                <X className="size-5" />
              </button>
            </div>

            {/* Navigation Links - Big Typography, Left Aligned */}
            <motion.nav
              className="flex-1 px-6 pt-8"
              variants={drawerMenuContainerVariants}
            >
              <ul className="flex flex-col gap-1">
                {filteredNavLinks.map((item) => (
                  <motion.li
                    key={item.id}
                    variants={drawerMenuVariants}
                  >
                    <a
                      href={item.href}
                      onClick={(e) => {
                        if (!item.href.startsWith('#')) {
                          setIsDrawerOpen(false);
                          return;
                        }
                        e.preventDefault();
                        if (pathname !== '/') {
                          router.push(`/${item.href}`);
                          setIsDrawerOpen(false);
                          return;
                        }
                        const element = document.getElementById(item.href.substring(1));
                        element?.scrollIntoView({ behavior: 'smooth' });
                        setIsDrawerOpen(false);
                      }}
                      className={`block py-3 text-4xl font-medium tracking-tight transition-colors ${
                        (item.href.startsWith('#') && pathname === '/' && activeSection === item.href.substring(1)) || (item.href === pathname)
                          ? 'text-foreground'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {item.name}
                    </a>
                  </motion.li>
                ))}
                {/* App Link */}
                <motion.li variants={drawerMenuVariants}>
                  <Link
                    href="/app"
                    onClick={() => setIsDrawerOpen(false)}
                    className={`block py-3 text-4xl font-medium tracking-tight transition-colors ${
                      pathname === '/app'
                        ? 'text-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    App
                  </Link>
                </motion.li>
              </ul>
            </motion.nav>

            {/* Footer Actions */}
            <div className="px-6 pb-8 mt-auto">
              <motion.div 
                className="flex flex-col gap-4"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.3 }}
              >
                {user ? (
                  <Link
                    href="/dashboard"
                    className="w-full h-14 text-lg font-medium rounded-xl bg-foreground text-background hover:bg-foreground/90 transition-colors inline-flex items-center justify-center"
                    onClick={() => setIsDrawerOpen(false)}
                  >
                    Dashboard
                  </Link>
                ) : (
                  <Link
                    href={ctaLink}
                    onClick={() => {
                      trackCtaSignup();
                      setIsDrawerOpen(false);
                    }}
                    className="w-full h-14 text-lg font-medium rounded-xl bg-foreground text-background hover:bg-foreground/90 transition-colors inline-flex items-center justify-center"
                    suppressHydrationWarning
                  >
                    {t('tryFree')}
                  </Link>
                )}
                
                {/* Theme Toggle */}
                <div className="flex items-center justify-between">
                  <ThemeToggle />
                </div>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
