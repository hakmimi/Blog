// Markdown links such as [x](/series/classification/artifacts/a.csv) are written
// root-relative so they survive moves; this prefixes the configured base path.
import { visit } from 'unist-util-visit';

export default function rehypeBase({ base = '/' } = {}) {
  const prefix = base.replace(/\/$/, '');
  return (tree) => {
    if (!prefix) return;
    // Raw HTML written inside Markdown (e.g. <script src="/js/x.js">) is still an unparsed 'raw' node here.
    // Only plain src/href are rewritten: data-src is left alone because the lab widgets add the base themselves.
    visit(tree, 'raw', (node) => {
      node.value = node.value.replace(/(\s(?:src|href)=")\/(?!\/)/g, (m, a) => a + prefix + '/');
    });
    visit(tree, 'element', (node) => {
      for (const key of ['href', 'src']) {
        const v = node.properties?.[key];
        if (typeof v === 'string' && v.startsWith('/') && !v.startsWith('//') && !v.startsWith(prefix + '/')) {
          node.properties[key] = prefix + v;
        }
      }
    });
  };
}
