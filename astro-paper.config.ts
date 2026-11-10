import { defineAstroPaperConfig } from "./src/types/config";

// TODO(Yitzhak): title, description and author in your own words.
export default defineAstroPaperConfig({
  site: {
    url: "https://hakmimi.github.io/",
    title: "Blog",
    description: "Notes from what I learn and build.",
    author: "Yitzhak",
    profile: "https://github.com/hakmimi",
    ogImage: "default-og.jpg",
    lang: "en",
    timezone: "Asia/Jerusalem",
    dir: "ltr",
  },
  posts: {
    perPage: 6,
    perIndex: 4,
  },
  features: {
    lightAndDarkMode: true,
    dynamicOgImage: true,
    showArchives: false, // the archive groups posts by publish month, which would show the dates
    showBackButton: true,
    editPost: { enabled: false },
    search: "pagefind",
    toc: true,
  },
  socials: [
    { name: "github", url: "https://github.com/hakmimi" },
  ],
  shareLinks: [
    { name: "x",        url: "https://x.com/intent/post?url=" },
    { name: "mail",     url: "mailto:?subject=See%20this%20post&body=" },
  ],
});
