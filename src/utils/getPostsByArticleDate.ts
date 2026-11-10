import type { CollectionEntry } from "astro:content";
import { postFilter } from "./postFilter";

type Post = CollectionEntry<"posts">;

/** The newest date among the articles a post evaluates (a post can test two articles). */
export function latestArticleDate(post: Post): number {
  const times = post.data.articles.map(a => a.date.getTime());
  return times.length > 0 ? Math.max(...times) : post.data.pubDatetime.getTime();
}

/**
 * Visible posts, newest article first. Ties (two articles from the same day) go to the post
 * published later. Publish dates still decide when a post goes live (postFilter); they are just not shown.
 */
export function getPostsByArticleDate(posts: Post[]): Post[] {
  return posts
    .filter(postFilter)
    .sort(
      (a, b) =>
        latestArticleDate(b) - latestArticleDate(a) ||
        b.data.pubDatetime.getTime() - a.data.pubDatetime.getTime()
    );
}
