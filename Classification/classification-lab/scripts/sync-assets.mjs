// Copies each series' figures / artifacts / code into public/series/<slug>/ so pages can link to them.
import { cp, mkdir, readdir, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';

await rm('public/series', { recursive: true, force: true });
if (!existsSync('series')) process.exit(0);
for (const slug of await readdir('series')) {
  const out = `public/series/${slug}`;
  for (const dir of ['figures', 'artifacts']) {
    if (existsSync(`series/${slug}/${dir}`)) {
      await mkdir(`${out}/${dir}`, { recursive: true });
      await cp(`series/${slug}/${dir}`, `${out}/${dir}`, { recursive: true, force: true });
    }
  }
  if (existsSync(`series/${slug}/scripts`)) {
    await mkdir(`${out}/code`, { recursive: true });
    await cp(`series/${slug}/scripts`, `${out}/code`, { recursive: true, force: true,
      filter: (src) => !src.includes('__pycache__') });
  }
}
