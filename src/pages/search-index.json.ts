import { articleUrl, getArticles, seriesBySlug } from '../lib/content';

export async function GET() {
  const articles = await getArticles();
  return new Response(JSON.stringify(articles.map((a) => ({
    url: articleUrl(a), series: seriesBySlug[a.data.series].title, title: a.data.title,
    description: a.data.description, keywords: a.data.keywords,
    text: (a.body ?? '').replace(/[#*`$\[\]()|]/g, ' ').replace(/\s+/g, ' ').slice(0, 14000),
  }))), { headers: { 'Content-Type': 'application/json' } });
}
