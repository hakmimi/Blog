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

export const allSeries: Series[] = [
  {
    slug: 'classification',
    title: 'Classification, Run for Real',
    tagline: 'From a bank-marketing spreadsheet to a model you can defend.',
    description:
      'One real dataset, twelve classifiers and a no-model baseline, every line of code. We tune, compare, calibrate and price the models — linear, trees, forests, XGBoost, LightGBM, CatBoost and more — and finish with a head-to-head leaderboard.',
    status: 'in-progress',
    started: '2026-09-30',
    keywords: ['classification', 'scikit-learn', 'xgboost', 'lightgbm', 'catboost', 'model comparison'],
    accent: '#168c84',
    cover: 'leaderboard-ap.png',
  },
  {
    slug: 'ai-engineering',
    title: 'AI Engineering, Day by Day',
    tagline: 'From a first endpoint to an audited, evaluated decision agent.',
    description:
      'Build two real systems one small step at a time: an Israel knowledge assistant (RAG, routing, memory, guardrails) and a payment-routing decision agent (rules, LLM second opinion, audit, evaluation). Every post says what changed, why, and how to run it.',
    status: 'in-progress',
    started: '2026-09-30',
    keywords: ['ai engineering', 'rag', 'langgraph', 'fastapi'],
    accent: '#2a6fbb',
  },
];

export const seriesBySlug = Object.fromEntries(allSeries.map((s) => [s.slug, s]));
