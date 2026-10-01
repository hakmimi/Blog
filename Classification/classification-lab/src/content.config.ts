import { defineCollection, z } from 'astro:content';
import { promises as fs } from 'node:fs';
import { relative } from 'node:path';
import { fileURLToPath } from 'node:url';

// A tiny local loader avoids platform-specific glob subprocess behavior while
// preserving Astro's normal Markdown parser, renderer, image imports, and schema.
const articleLoader = {
  name: 'classification-lab-articles',
  async load(context: any) {
    const { config, entryTypes, generateDigest, parseData, store } = context;
    const base = new URL('./src/content/articles/', config.root);
    // series are sub-folders: articles/<series>/<nn-slug>.md  ->  id '<series>/<nn-slug>'
    const names = (await fs.readdir(base, { recursive: true }))
      .map((n) => n.split('\\').join('/'))
      .filter((name) => name.endsWith('.md'))
      .sort();
    const entryType = entryTypes.get('.md');
    if (!entryType) throw new Error('Astro Markdown entry type is unavailable');
    const render = await entryType.getRenderFunction(config);
    store.clear();
    for (const name of names) {
      const fileUrl = new URL(name, base);
      const filePath = fileURLToPath(fileUrl);
      const contents = await fs.readFile(fileUrl, 'utf-8');
      const { body, data } = await entryType.getEntryInfo({ contents, fileUrl });
      const id = name.replace(/\.md$/, '');
      const digest = generateDigest(contents);
      const parsedData = await parseData({ id, data, filePath });
      const rendered = await render({ id, data, body, filePath, digest });
      store.set({
        id,
        data: parsedData,
        body,
        filePath: relative(fileURLToPath(config.root), filePath).replaceAll('\\', '/'),
        digest,
        rendered,
        assetImports: rendered?.metadata?.imagePaths,
      });
    }
  },
};

const articles = defineCollection({
  loader: articleLoader as any,
  schema: z.object({
    title: z.string(),
    description: z.string(),
    series: z.string(),
    order: z.number(),
    date: z.coerce.date(),                 // first published
    updated: z.coerce.date().optional(),   // last substantive edit
    keywords: z.array(z.string()).min(1),
    readingTime: z.string(),
    figure: z.string().optional(),         // file name under series/<series>/figures/
    draft: z.boolean().default(false),
  }),
});

export const collections = { articles };
