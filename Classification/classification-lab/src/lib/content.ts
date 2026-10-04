import { getCollection, type CollectionEntry } from 'astro:content';
import { allSeries, seriesBySlug } from '../data/series';

export type Article = CollectionEntry<'articles'>;
export const base = import.meta.env.BASE_URL.replace(/\/$/, '');

export const slugify = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
export const fmtDate = (d: Date) => d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
export const iso = (d: Date) => d.toISOString().slice(0, 10);

export const articleUrl = (a: Article) => `${base}${a.data.lang === 'he' ? '/he' : ''}/series/${a.data.series}/${a.id.split('/').pop()}/`;
export const seriesUrl = (slug: string) => `${base}/series/${slug}/`;
export const topicUrl = (k: string) => `${base}/topics/${slugify(k)}/`;
export const assetUrl = (series: string, kind: 'figures' | 'artifacts' | 'code', file: string) =>
  `${base}/series/${series}/${kind}/${file}`;

/** Published articles. Within a series: reading order. Across series: newest first. */
export async function getArticles(series?: string): Promise<Article[]> {
  const all = (await getCollection('articles')).filter((a) => !a.data.draft && a.data.lang === 'en');
  return all
    .filter((a) => !series || a.data.series === series)
    .sort((a, b) => (a.data.series === b.data.series ? a.data.order - b.data.order : +b.data.date - +a.data.date));
}

/** Hebrew translations (kept out of getArticles so indexes, topics and search stay English). */
export async function getHebrewArticles(series?: string): Promise<Article[]> {
  const all = (await getCollection('articles')).filter((a) => !a.data.draft && a.data.lang === 'he');
  return all.filter((a) => !series || a.data.series === series).sort((a, b) => a.data.order - b.data.order);
}

export const slugOf = (a: Article) => a.id.split('/').pop() as string;

export async function getTopics(): Promise<Map<string, { label: string; articles: Article[] }>> {
  const topics = new Map<string, { label: string; articles: Article[] }>();
  for (const a of await getArticles()) {
    for (const k of a.data.keywords) {
      const key = slugify(k);
      if (!topics.has(key)) topics.set(key, { label: k, articles: [] });
      topics.get(key)!.articles.push(a);
    }
  }
  return topics;
}

export { allSeries, seriesBySlug };
