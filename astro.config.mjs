import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { unified } from '@astrojs/markdown-remark';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeBase from './src/plugins/rehype-base.mjs';

const base = process.env.BASE_PATH || '/';

export default defineConfig({
  site: process.env.SITE_URL || 'https://example.github.io',
  base,
  output: 'static',
  integrations: [sitemap()],
  markdown: {
    processor: unified({ remarkPlugins: [remarkMath], rehypePlugins: [rehypeKatex, [rehypeBase, { base }]] }),
    shikiConfig: { theme: 'github-dark' }
  }
});
