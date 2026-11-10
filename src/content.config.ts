import { defineCollection } from "astro:content";
import { z } from "astro/zod";
import { glob } from "astro/loaders";
import config from "@/config";
import { SOURCE_KEYS } from "@/utils/sources";

export const BLOG_PATH = "src/content/posts";

const posts = defineCollection({
  loader: glob({ pattern: "**/[^_]*.{md,mdx}", base: `./${BLOG_PATH}` }),
  schema: ({ image }) =>
    z.object({
      author: z.string().default(config.site.author),
      pubDatetime: z.date(),
      modDatetime: z.date().optional().nullable(),
      title: z.string(),
      featured: z.boolean().optional(),
      draft: z.boolean().optional(),
      tags: z.array(z.string()).default(["others"]),
      // Company whose article the post tests; its logo shows next to the title.
      source: z.array(z.enum(SOURCE_KEYS)).default([]),
      // The article(s) the post tests: shown under the title, and used to place the post on the Timeline page.
      articles: z
        .array(
          z.object({
            publisher: z.string(),
            title: z.string(),
            url: z.string().url(),
            date: z.coerce.date(),
          })
        )
        .default([]),
      // The ai-engineering-lab folder(s) under topics/ this post reports on, e.g. "07-text-to-sql-where-it-breaks".
      // Not shown on the site; it is the link from a post (whose URL has no number) back to its code in git.
      topics: z.array(z.string()).default([]),
      ogImage: image().or(z.string()).optional(),
      description: z.string(),
      canonicalURL: z.string().optional(),
      hideEditPost: z.boolean().optional(),
      hideToc: z.boolean().optional(),
      // An empty value means "not set", so the site timezone applies.
      timezone: z
        .string()
        .optional()
        .transform(tz => tz || undefined),
    }),
});

const pages = defineCollection({
  loader: glob({ pattern: "**/[^_]*.{md,mdx}", base: "./src/content/pages" }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    ogImage: z.string().optional(),
    canonicalURL: z.string().optional(),
  }),
});

export const collections = { posts, pages };
