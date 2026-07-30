## Speekify website

The public landing page is an Astro project. Run these commands from `site/`
(`cd site` from the repository root):

| Command                   | Action                                           |
| :------------------------ | :----------------------------------------------- |
| `npm install`             | Installs dependencies                            |
| `npm run dev -- --background` | Starts the managed local dev server at `localhost:4321` |
| `npm run astro -- dev status` | Shows the managed dev-server status          |
| `npm run astro -- dev stop` | Stops the managed dev server                    |
| `npm run build`           | Build your production site to `./dist/`          |
| `npm run preview`         | Preview your build locally, before deploying     |
| `npm run astro ...`       | Run CLI commands like `astro add`, `astro check` |
| `npm run astro -- --help` | Get help using the Astro CLI                     |

Product behavior and installation claims on the site are maintained in
`src/i18n/content.ts`; keep the English and French copies aligned with the root
README and `docs/usage.md`.

## Astro documentation

Feel free to check [our documentation](https://docs.astro.build)
