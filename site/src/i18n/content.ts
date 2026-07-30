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
			"Speekify is an open-source CLI that turns articles, PDFs, YouTube transcripts, piped text, and source batches into local audio. Synthesis and durable execution run on your machine.",
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
			"Speekify converts articles, PDFs, YouTube transcripts, and piped text into local audio. Synthesis stays on your machine; URL content is fetched only from the source you request.",
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
				body: "Audio and durable workflow state stay on your machine. URL extraction still contacts the source you request.",
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
				body: "Inline text, stdin, local .txt/.md/.text/.pdf files, readable URLs, YouTube transcripts, and recursive batches.",
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
				title: "Reliable batches",
				body: "A loopback-only Temporal service retries local work, preserves progress on disk, and generates one WAV per batch item.",
			},
			{
				title: "MCP server",
				body: "Expose single and batch generation as tools for AI assistants.",
			},
		],
	},
	how: {
		title: "From install to audio in five steps.",
		steps: [
			{
				title: "Install Speekify.",
				body: "Homebrew on Apple Silicon macOS, or pip/pipx/uv on supported macOS and Linux systems.",
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
			"Generate one WAV per file, URL, text item, or directory document",
		],
		fullRef: "Full command reference →",
	},
	mcp: {
		title: "Let your AI assistant make the audio.",
		subtitle:
			"Speekify ships a local Model Context Protocol server, so assistants can call it as a tool inside their automations.",
		body: "Start the server with one command and Speekify becomes available to MCP-capable clients — Claude Code, GitHub Copilot, Codex, and OpenAI's remote MCP. It exposes speekify_generate_wav, speekify_generate_batch, generation defaults, and a news recap prompt. Audio synthesis and Temporal stay on the Speekify host; remote MCP arguments still travel through the selected client transport.",
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
				body: "Use speekify batch with files, URLs, or a directory to create one WAV per source.",
			},
			{
				title: "Automated reading via an AI agent",
				body: "Have an assistant fetch, summarize, and hand text to Speekify through MCP — and get back a file to play.",
			},
		],
	},
	install: {
		title: "Install Speekify.",
		subtitle: "Homebrew on Apple Silicon macOS, pip/pipx/uv on macOS and Linux, or source with uv.",
		brewLabel: "Apple Silicon macOS — Homebrew (no Python or uv required)",
		sourceLabel: "From source (uv)",
		pypiLabel: "pip / pipx / uv — from PyPI",
		note: "Run speekify setup once to warm the AI models. Homebrew installs Temporal as a dependency; pip/pipx/uv securely provision the pinned Temporal CLI on first generation (macOS/Linux arm64 or amd64). The local service stops after five idle minutes and reuses its persisted state next time.",
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
			"Speekify est un CLI open source qui transforme articles, PDF, transcriptions YouTube, texte redirigé et lots de sources en audio local. La synthèse et l'exécution durable tournent sur votre machine.",
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
			"Speekify convertit articles, PDF, transcriptions YouTube et texte redirigé en audio local. La synthèse reste sur votre machine ; une URL n'est récupérée que depuis la source que vous demandez.",
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
				body: "L'audio et l'état durable restent sur votre machine. L'extraction d'une URL contacte tout de même la source demandée.",
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
				body: "Texte en ligne, stdin, fichiers .txt/.md/.text/.pdf, URL lisibles, transcriptions YouTube et lots récursifs.",
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
				title: "Lots fiables",
				body: "Un service Temporal lié à l'interface locale relance le travail, conserve la progression sur disque et crée un WAV par élément.",
			},
			{
				title: "Serveur MCP",
				body: "Exposez la génération unitaire et par lots comme outils pour les assistants IA.",
			},
		],
	},
	how: {
		title: "De l'installation à l'audio en cinq étapes.",
		steps: [
			{
				title: "Installez Speekify.",
				body: "Homebrew sur macOS Apple Silicon, ou pip/pipx/uv sur les systèmes macOS et Linux pris en charge.",
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
			"Créer un WAV par fichier, URL, texte ou document d'un dossier",
		],
		fullRef: "Référence complète des commandes →",
	},
	mcp: {
		title: "Laissez votre assistant IA générer l'audio.",
		subtitle:
			"Speekify embarque un serveur Model Context Protocol local, pour que les assistants l'appellent comme un outil dans leurs automatisations.",
		body: "Démarrez le serveur d'une commande pour exposer speekify_generate_wav, speekify_generate_batch, les valeurs par défaut et un prompt de synthèse d'actualités. L'audio et Temporal restent sur l'hôte Speekify ; avec un MCP distant, les arguments passent tout de même par le transport du client.",
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
				body: "Utilisez speekify batch avec des fichiers, des URL ou un dossier pour créer un WAV par source.",
			},
			{
				title: "Lecture automatisée via un agent IA",
				body: "Laissez un assistant récupérer, résumer et transmettre du texte à Speekify via MCP — et récupérez un fichier à lire.",
			},
		],
	},
	install: {
		title: "Installez Speekify.",
		subtitle: "Homebrew sur macOS Apple Silicon, pip/pipx/uv sur macOS et Linux, ou les sources avec uv.",
		brewLabel: "macOS Apple Silicon — Homebrew (ni Python ni uv requis)",
		sourceLabel: "Depuis les sources (uv)",
		pypiLabel: "pip / pipx / uv — depuis PyPI",
		note: "Lancez speekify setup une fois pour préchauffer les modèles IA. Homebrew installe Temporal comme dépendance ; pip/pipx/uv provisionnent le CLI Temporal épinglé à la première génération (macOS/Linux arm64 ou amd64). Le service local s'arrête après cinq minutes d'inactivité et réutilise ensuite son état persistant.",
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
