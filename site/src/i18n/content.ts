// Single source of all UI copy, in English and French.
// Components read `getContent(Astro.currentLocale)` — no prop drilling.
// Commands/code live in the components (locale-agnostic); only prose lives here.

export type Lang = "en" | "fr";

export const languages: Record<Lang, string> = { en: "English", fr: "Français" };
export const defaultLang: Lang = "en";

const en = {
	meta: {
		title: "Speekify — Turn text into local audio from your terminal",
		description:
			"Speekify is an open-source CLI that turns articles, PDFs, YouTube transcripts, and piped text into a local audio file, synthesized on your own machine. Multilingual, with an MCP server for AI workflows.",
	},
	nav: {
		how: "How it works",
		cli: "CLI",
		mcp: "MCP",
		install: "Install",
		github: "GitHub",
		getStarted: "Get started",
		menu: "Menu",
	},
	hero: {
		badge: "Local TTS",
		badgeText: "Runs locally with Supertonic v3 — no audio leaves your machine",
		title: "Turn anything you'd read into something you can hear.",
		description:
			"Speekify is an open-source CLI that converts articles, PDFs, YouTube transcripts, and piped text into a local audio file — synthesized on your own machine. Nothing you read leaves your computer.",
		getStarted: "Get started",
		viewGithub: "View on GitHub",
		caption: "Output is a .wav file in your current folder.",
	},
	why: {
		title: "Your reading list became a backlog.",
		subtitle: "Not everything worth knowing deserves your screen time.",
		body: "There's more to read than there are hours to sit and read it — saved articles, long PDFs, talks you bookmarked and never opened. Most of it doesn't need your eyes. It needs twenty minutes of your attention, which you already have on a walk, a commute, or while doing the dishes. Speekify converts the text into audio so you can clear the backlog without sitting still for it.",
		cards: [
			{ title: "Listen anywhere", body: "Take your backlog on a walk, a commute, or the dishes." },
			{
				title: "Local & private",
				body: "Audio is synthesized on your machine. Nothing you read leaves your computer.",
			},
			{ title: "One command", body: "Point Speekify at a source and get a file back." },
		],
	},
	what: {
		title: "One command, many sources, a file you can play anywhere.",
		subtitle: "Speekify reads from where your content already lives and writes a plain audio file.",
		cards: [
			{
				title: "Many input sources",
				body: "Inline text, stdin, local .txt/.md/.pdf files, readable URLs, and YouTube transcripts. Auto-detected.",
			},
			{
				title: "Local synthesis",
				body: "Audio is generated on your machine with Supertonic v3. No audio leaves your computer.",
			},
			{
				title: "Multilingual",
				body: "en, fr, de, es, it, pt, ja, ko, and more, plus na for language-agnostic synthesis. By default Speekify auto-detects the source language and speaks it back — English in, English out. Pass --lang fr to translate English input to French before synthesis.",
			},
			{
				title: "Voice control",
				body: "10 built-in voices (M1–M5, F1–F5), custom Voice Builder JSON styles, plus speed and synthesis-step tuning.",
			},
			{
				title: "MCP server",
				body: "Expose Speekify as a tool so AI assistants can generate audio inside your automations.",
			},
			{ title: "Open source", body: "MIT licensed. Read the code, file an issue, send a patch." },
		],
	},
	how: {
		title: "From install to audio in five steps.",
		steps: [
			{
				title: "Install Speekify.",
				body: "Homebrew on macOS, from source with uv, or from PyPI.",
			},
			{
				title: "Run setup once.",
				body: "<code>speekify setup</code> downloads and warms the local model so the first real run is fast.",
			},
			{
				title: "Give it a source.",
				body: "Pass inline text, a URL, a file path, or pipe text in — Speekify detects the type automatically.",
			},
			{
				title: "Get a WAV.",
				body: "Speekify writes a .wav file to your current folder (or wherever --output-dir points). Play it anywhere.",
			},
			{
				title: "Optional: wire it into your AI workflow.",
				body: "Run <code>speekify mcp</code> to let an assistant like Claude Code or Codex generate audio as a tool call.",
			},
		],
	},
	cli: {
		title: "Real commands, copy-paste ready.",
		subtitle: "Every example works with the installed binary, or with uv run speekify … from a source checkout.",
		labels: [
			"Inline text",
			"A readable web article",
			"A local PDF",
			"A YouTube video (quote URLs with ? or &)",
			"Pipe text from stdin",
			"Pick a voice and output folder",
		],
		fullRef: "Full command reference →",
	},
	mcp: {
		title: "Let your AI assistant make the audio.",
		subtitle:
			"Speekify ships a local Model Context Protocol server, so assistants can call it as a tool inside their automations.",
		body: "Start the server with one command and Speekify becomes available to MCP-capable clients — Claude Code, GitHub Copilot, Codex, and OpenAI's remote MCP. The server exposes speekify_generate_wav (text, URL, or file → WAV with structured details), speekify_generation_defaults (supported voices, languages, and ranges), and a news_recap_to_audio prompt template. The audio is still generated locally on your machine.",
		startLabel: "Start the MCP server",
		addLabel: "Add to Claude Code",
		perClient: "Per-client setup →",
	},
	useCases: {
		title: "What people use it for.",
		cases: [
			{
				title: "Article → audio",
				body: "Drop in a URL, get the readable body of the page as a .wav to listen to later.",
			},
			{
				title: "PDF → audio",
				body: "Turn a text-based report or paper into audio for the commute. (Text-based PDFs only — scanned image PDFs have no text to read.)",
			},
			{
				title: "YouTube transcript → audio",
				body: "Pull a video's captions and listen instead of watching. Add --lang fr to hear an English video in French.",
			},
			{
				title: "News & tech veille",
				body: "Batch your reading into audio you can get through while doing something else.",
			},
			{
				title: "Automated reading via an AI agent",
				body: "Have an assistant fetch, summarize, and hand text to Speekify through MCP — and get back a file to play.",
			},
		],
	},
	install: {
		title: "Install Speekify.",
		subtitle: "Homebrew, from source, or from PyPI — all work today.",
		brewLabel: "macOS — Homebrew (no Python or uv required)",
		sourceLabel: "From source (uv)",
		pypiLabel: "pip / pipx / uv — from PyPI",
		note: "Run speekify setup once after installing. It downloads and warms the local Supertonic model (and, by default, the English→French translation model). Skip it and the models download automatically on first use.",
	},
	openSource: {
		badge: "MIT Licensed",
		title: "Open source, MIT licensed.",
		body: "Speekify is built by Otterly Space Labs and released under the MIT license. The code is on GitHub — read it, open an issue, or send a pull request. If it's useful to you, a star helps other people find it.",
		star: "Star on GitHub",
		report: "Report an issue",
	},
	footer: {
		tagline: "Open-source CLI that turns text into local audio.",
		links: ["GitHub", "Documentation", "CLI Reference", "MCP Setup"],
		license: "MIT License · © 2026 Otterly Space SARL",
		disclaimer:
			"Speekify only fetches content you point it at, for your personal use. You're responsible for respecting the terms of service and copyright of any source you extract from.",
	},
} as const;

type Content = typeof en;

const fr: Content = {
	meta: {
		title: "Speekify — Transformez du texte en audio local depuis votre terminal",
		description:
			"Speekify est un CLI open source qui transforme articles, PDF, transcriptions YouTube et texte redirigé en fichier audio local, synthétisé sur votre propre machine. Multilingue, avec un serveur MCP pour vos workflows IA.",
	},
	nav: {
		how: "Fonctionnement",
		cli: "CLI",
		mcp: "MCP",
		install: "Installation",
		github: "GitHub",
		getStarted: "Commencer",
		menu: "Menu",
	},
	hero: {
		badge: "TTS local",
		badgeText: "Fonctionne en local avec Supertonic v3 — aucun audio ne quitte votre machine",
		title: "Transformez tout ce que vous liriez en quelque chose à écouter.",
		description:
			"Speekify est un CLI open source qui convertit articles, PDF, transcriptions YouTube et texte redirigé en fichier audio local — synthétisé sur votre propre machine. Rien de ce que vous lisez ne quitte votre ordinateur.",
		getStarted: "Commencer",
		viewGithub: "Voir sur GitHub",
		caption: "Le résultat est un fichier .wav dans votre dossier courant.",
	},
	why: {
		title: "Votre liste de lecture est devenue un arriéré.",
		subtitle: "Tout ce qui mérite d'être su ne mérite pas votre temps d'écran.",
		body: "Il y a plus à lire que d'heures pour s'asseoir et le lire — articles enregistrés, longs PDF, conférences mises de côté et jamais ouvertes. La plupart n'ont pas besoin de vos yeux. Il leur faut vingt minutes de votre attention, que vous avez déjà en marchant, dans les transports ou en faisant la vaisselle. Speekify convertit le texte en audio pour vider l'arriéré sans avoir à rester immobile.",
		cards: [
			{ title: "Écoutez partout", body: "Emportez votre arriéré en balade, dans les transports ou à la vaisselle." },
			{
				title: "Local et privé",
				body: "L'audio est synthétisé sur votre machine. Rien de ce que vous lisez ne quitte votre ordinateur.",
			},
			{ title: "Une seule commande", body: "Pointez Speekify vers une source et récupérez un fichier." },
		],
	},
	what: {
		title: "Une commande, de multiples sources, un fichier lisible partout.",
		subtitle: "Speekify lit là où votre contenu se trouve déjà et écrit un simple fichier audio.",
		cards: [
			{
				title: "De multiples sources",
				body: "Texte en ligne, stdin, fichiers locaux .txt/.md/.pdf, URL lisibles et transcriptions YouTube. Détection automatique.",
			},
			{
				title: "Synthèse locale",
				body: "L'audio est généré sur votre machine avec Supertonic v3. Aucun audio ne quitte votre ordinateur.",
			},
			{
				title: "Multilingue",
				body: "en, fr, de, es, it, pt, ja, ko et plus, ainsi que na pour une synthèse indépendante de la langue. Par défaut, Speekify détecte la langue source et la restitue — anglais en entrée, anglais en sortie. Ajoutez --lang fr pour traduire le texte anglais en français avant la synthèse.",
			},
			{
				title: "Contrôle de la voix",
				body: "10 voix intégrées (M1–M5, F1–F5), styles JSON personnalisés via Voice Builder, plus réglage de la vitesse et du nombre d'étapes de synthèse.",
			},
			{
				title: "Serveur MCP",
				body: "Exposez Speekify comme outil pour que les assistants IA génèrent de l'audio dans vos automatisations.",
			},
			{ title: "Open source", body: "Sous licence MIT. Lisez le code, ouvrez une issue, envoyez un correctif." },
		],
	},
	how: {
		title: "De l'installation à l'audio en cinq étapes.",
		steps: [
			{
				title: "Installez Speekify.",
				body: "Homebrew sur macOS, depuis les sources avec uv, ou depuis PyPI.",
			},
			{
				title: "Lancez la configuration une fois.",
				body: "<code>speekify setup</code> télécharge et préchauffe le modèle local pour que la première vraie exécution soit rapide.",
			},
			{
				title: "Donnez-lui une source.",
				body: "Passez du texte en ligne, une URL, un chemin de fichier, ou redirigez du texte — Speekify détecte le type automatiquement.",
			},
			{
				title: "Récupérez un WAV.",
				body: "Speekify écrit un fichier .wav dans votre dossier courant (ou là où pointe --output-dir). Lisez-le n'importe où.",
			},
			{
				title: "Optionnel : intégrez-le à votre workflow IA.",
				body: "Lancez <code>speekify mcp</code> pour qu'un assistant comme Claude Code ou Codex génère de l'audio via un appel d'outil.",
			},
		],
	},
	cli: {
		title: "De vraies commandes, prêtes à copier-coller.",
		subtitle: "Chaque exemple fonctionne avec le binaire installé, ou avec uv run speekify … depuis une copie des sources.",
		labels: [
			"Texte en ligne",
			"Un article web lisible",
			"Un PDF local",
			"Une vidéo YouTube (mettez les URL avec ? ou & entre guillemets)",
			"Rediriger du texte depuis stdin",
			"Choisir une voix et un dossier de sortie",
		],
		fullRef: "Référence complète des commandes →",
	},
	mcp: {
		title: "Laissez votre assistant IA générer l'audio.",
		subtitle:
			"Speekify embarque un serveur Model Context Protocol local, pour que les assistants l'appellent comme un outil dans leurs automatisations.",
		body: "Démarrez le serveur d'une seule commande et Speekify devient disponible pour les clients compatibles MCP — Claude Code, GitHub Copilot, Codex et le MCP distant d'OpenAI. Le serveur expose speekify_generate_wav (texte, URL ou fichier → WAV avec détails structurés), speekify_generation_defaults (voix, langues et plages prises en charge), et un modèle de prompt news_recap_to_audio. L'audio reste généré localement sur votre machine.",
		startLabel: "Démarrer le serveur MCP",
		addLabel: "Ajouter à Claude Code",
		perClient: "Configuration par client →",
	},
	useCases: {
		title: "Ce pour quoi on l'utilise.",
		cases: [
			{
				title: "Article → audio",
				body: "Collez une URL, récupérez le corps lisible de la page en .wav à écouter plus tard.",
			},
			{
				title: "PDF → audio",
				body: "Transformez un rapport ou un article textuel en audio pour les trajets. (PDF textuels uniquement — les PDF scannés n'ont pas de texte à lire.)",
			},
			{
				title: "Transcription YouTube → audio",
				body: "Récupérez les sous-titres d'une vidéo et écoutez au lieu de regarder. Ajoutez --lang fr pour écouter en français une vidéo en anglais.",
			},
			{
				title: "Actualités et veille tech",
				body: "Regroupez vos lectures en audio à parcourir pendant que vous faites autre chose.",
			},
			{
				title: "Lecture automatisée via un agent IA",
				body: "Laissez un assistant récupérer, résumer et transmettre du texte à Speekify via MCP — et récupérez un fichier à lire.",
			},
		],
	},
	install: {
		title: "Installez Speekify.",
		subtitle: "Homebrew, depuis les sources ou depuis PyPI — tout fonctionne dès aujourd'hui.",
		brewLabel: "macOS — Homebrew (ni Python ni uv requis)",
		sourceLabel: "Depuis les sources (uv)",
		pypiLabel: "pip / pipx / uv — depuis PyPI",
		note: "Lancez speekify setup une fois après l'installation. Il télécharge et préchauffe le modèle Supertonic local (et, par défaut, le modèle de traduction anglais→français). Sautez cette étape et les modèles se téléchargeront automatiquement à la première utilisation.",
	},
	openSource: {
		badge: "Sous licence MIT",
		title: "Open source, sous licence MIT.",
		body: "Speekify est développé par Otterly Space Labs et publié sous licence MIT. Le code est sur GitHub — lisez-le, ouvrez une issue ou envoyez une pull request. S'il vous est utile, une étoile aide d'autres personnes à le trouver.",
		star: "Mettre une étoile sur GitHub",
		report: "Signaler un problème",
	},
	footer: {
		tagline: "CLI open source qui transforme du texte en audio local.",
		links: ["GitHub", "Documentation", "Référence CLI", "Configuration MCP"],
		license: "Licence MIT · © 2026 Otterly Space SARL",
		disclaimer:
			"Speekify ne récupère que le contenu que vous lui indiquez, pour votre usage personnel. Il vous appartient de respecter les conditions d'utilisation et le droit d'auteur de toute source dont vous extrayez du contenu.",
	},
};

export const content: Record<Lang, Content> = { en, fr };

export function getContent(locale?: string): Content {
	return content[locale === "fr" ? "fr" : "en"];
}
