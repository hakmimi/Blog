// Every series on the blog is declared here. Articles point at a series by `slug`.
// To add a series: add an entry, create src/content/articles/<slug>/, and (optionally)
// series/<slug>/{scripts,artifacts,figures} for the code and outputs it publishes.
export interface Series {
  slug: string;
  title: string;
  tagline: string;
  description: string;
  status: 'in-progress' | 'complete';
  started: string;       // ISO date
  keywords: string[];
  accent: string;        // css colour used on cards
  cover?: string;        // path under /series/<slug>/figures/
}

export const allSeries: Series[] = [];

export const seriesBySlug: Record<string, Series> = Object.fromEntries(allSeries.map((s) => [s.slug, s]));
