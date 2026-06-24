import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://otterlyspacelabs.github.io',
  base: '/speekify',
  integrations: [sitemap()],

  vite: {
    plugins: [tailwindcss()]
  }
});