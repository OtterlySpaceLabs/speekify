import { getAbsoluteLocaleUrl, getRelativeLocaleUrl } from "astro:i18n";
import { defaultLang, type Lang } from "./content";

const locales: Lang[] = ["en", "fr"];

// Strip base + locale prefix to get the route-relative path shared across locales.
function logicalPath(pathname: string, current: string): string {
	const base = import.meta.env.BASE_URL.replace(/\/$/, "");
	let p = pathname.startsWith(base) ? pathname.slice(base.length) : pathname;
	if (current !== defaultLang) p = p.replace(new RegExp(`^/${current}(?=/|$)`), "");
	return p || "/";
}

export interface Alternate {
	locale: Lang;
	abs: string; // absolute URL — for hreflang
	rel: string; // base-prefixed path — for in-page links
}

export function getAlternates(pathname: string, current: string): Alternate[] {
	const path = logicalPath(pathname, current);
	return locales.map((locale) => ({
		locale,
		abs: getAbsoluteLocaleUrl(locale, path),
		rel: getRelativeLocaleUrl(locale, path),
	}));
}
