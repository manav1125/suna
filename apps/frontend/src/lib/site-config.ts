import { pricingTiers, type PricingTier } from '@/lib/pricing-config';

// Re-export for backward compatibility
export type { PricingTier } from '@/lib/pricing-config';

export const siteConfig = {
  url: process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
  nav: {
    links: [
      { id: 1, name: 'Home', href: '/' },
      { id: 2, name: 'About', href: '/about' },
      { id: 3, name: 'Pricing', href: '/pricing' },
      { id: 4, name: 'Tutorials', href: '/tutorials' },
    ],
  },
  hero: {
    description:
      "Build, grow, and scale your venture with VentureVerse, the AI Venture Operating System.",
  },
  cloudPricingItems: pricingTiers,
  footerLinks: [
    {
      title: 'VentureVerse',
      links: [
        { id: 1, title: 'About', url: '/about' },
        { id: 2, title: 'Careers', url: '/careers' },
        { id: 3, title: 'Support', url: '/support' },
        { id: 4, title: 'Contact', url: 'https://ventureverse.com/contact' },
        { id: 5, title: 'Tutorials', url: '/tutorials' },
        { id: 6, title: 'VentureVerse.com', url: 'https://ventureverse.com' },
      ],
    },
  ],
};

export type SiteConfig = typeof siteConfig;
