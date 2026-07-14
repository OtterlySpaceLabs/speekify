// Single source of all UI copy, in English and French.
// Components read `getContent(Astro.currentLocale)` — no prop drilling.
// Commands/code live in the components (locale-agnostic); only prose lives here.

export type Lang = "en" | "fr";

export const languages: Record<Lang, string> = { en: "English", fr: "Français" };
export const defaultLang: Lang = "en";

const en = {
	meta: {
		title: "Speekify — Local text-to-speech CLI for articles, PDFs and YouTube",
		description:
			"Speekify is an open-source local text-to-speech CLI that converts articles, PDFs, YouTube transcripts, files and stdin into private WAV audio with Supertonic v3.",
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
		badge: "Open-source local text-to-speech CLI",
		badgeText: "Open source · private by design · yours to keep",
		title: "Articles, PDFs, videos: everything becomes audio.",
		titleAccent: "Listen wherever you want.",
		description:
			"Speekify converts articles, text-based PDFs, YouTube transcripts, local files and stdin into natural WAV audio on your own machine — no account, no cloud, no lock-in.",
		getStarted: "Create your first audio",
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
		title: "Everything you saved for later. Finally listenable.",
		subtitle: "Keep your habits. Paste the source you already have; Speekify hands you back an audio file you actually own.",
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
		title: "Your reading queue, one command lighter.",
		subtitle: "No dashboard to learn. Point Speekify at what matters, press Enter, and take the result with you.",
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
		title: "Give your automations a voice.",
		subtitle:
			"Your assistant can turn a briefing, a recap, or a research trail into audio while the entire synthesis stays on your machine.",
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
		title: "Your first listen starts here.",
		subtitle: "Choose your route. In a few minutes, your next read can leave the screen with you.",
		brewLabel: "macOS — Homebrew (no Python or uv required)",
		sourceLabel: "From source (uv)",
		pypiLabel: "pip / pipx / uv — from PyPI",
		note: "Install Speekify, run setup once, then turn your first link into audio. The local models are downloaded and warmed automatically; every listen after that stays ready on your machine.",
	},
	openSource: {
		badge: "MIT Licensed",
		title: "Use it today. Shape what comes next.",
		body: "Speekify is built in the open under the MIT license. Inspect every line, propose the voice or workflow you need, and help make local audio useful to more people.",
		star: "Join the project on GitHub",
		report: "Report an issue",
	},
	faq: {
		title: "Questions, answered before the install.",
		subtitle: "The practical details about local text-to-speech, supported sources, privacy, voices, and AI integrations.",
		items: [
			{
				question: "What is Speekify?",
				answer: "Speekify is an open-source command-line text-to-speech tool. It extracts readable text from inline input, stdin, local text files, text-based PDFs, web articles, and YouTube transcripts, then creates a local WAV file with Supertonic v3.",
			},
			{
				question: "Does Speekify send my documents to the cloud?",
				answer: "No. Voice synthesis runs on your machine and the generated WAV stays local. When you provide a web or YouTube URL, Speekify must retrieve that public source, but it does not upload your extracted text to a remote speech service.",
			},
			{
				question: "Which inputs and audio formats are supported?",
				answer: "Speekify accepts inline text, piped stdin, .txt and .md files, text-based PDFs, readable web URLs, and YouTube transcripts. It currently writes standard WAV audio files.",
			},
			{
				question: "Which languages and voices are available?",
				answer: "Speekify auto-detects the source language and supports many Supertonic languages, including English, French, German, Spanish, Italian, Portuguese, Japanese, and Korean. Ten built-in voices are available, plus custom Voice Builder JSON styles.",
			},
			{
				question: "Can an AI assistant use Speekify?",
				answer: "Yes. The built-in MCP server exposes local audio generation as a tool for compatible clients such as Claude Code, Codex, and GitHub Copilot, while synthesis remains on your computer.",
			},
			{
				question: "How do I install Speekify?",
				answer: "Install the standalone Homebrew package on macOS, or install the Python package with pipx or uv. Run speekify setup once to download and warm the local speech model, then pass text, a file, or a URL to the speekify command.",
			},
		],
	},
	footer: {
		tagline: "Your reading, in motion — open source and made locally.",
		links: ["GitHub", "Documentation", "CLI Reference", "MCP Setup"],
		license: "MIT License · © 2026 Otterly Space SARL",
		disclaimer:
			"Speekify only fetches content you point it at, for your personal use. You're responsible for respecting the terms of service and copyright of any source you extract from.",
	},
} as const;

type Content = typeof en;

const fr: Content = {
	meta: {
		title: "Speekify — Synthèse vocale locale pour articles, PDF et YouTube",
		description:
			"Speekify, CLI open source de synthèse vocale locale, convertit articles, PDF, transcriptions YouTube, fichiers et stdin en audio WAV privé avec Supertonic v3.",
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
		badge: "CLI open source de synthèse vocale locale",
		badgeText: "Open source · privé par conception · à vous pour toujours",
		title: "Articles, PDF, vidéos : tout devient audio.",
		titleAccent: "Écoutez-les où vous voulez.",
		description:
			"Speekify convertit articles, PDF textuels, transcriptions YouTube, fichiers locaux et stdin en audio WAV naturel sur votre propre machine — sans compte, sans cloud, sans dépendance.",
		getStarted: "Créer mon premier audio",
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
		title: "Tout ce que vous gardez pour plus tard. Enfin écoutable.",
		subtitle: "Ne changez pas vos habitudes. Donnez la source que vous avez déjà ; Speekify vous rend un fichier audio qui vous appartient vraiment.",
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
		title: "Votre pile de lecture, une commande plus légère.",
		subtitle: "Aucun tableau de bord à apprendre. Indiquez ce qui compte, appuyez sur Entrée et emportez le résultat.",
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
		title: "Donnez une voix à vos automatisations.",
		subtitle:
			"Votre assistant peut transformer un briefing, un récapitulatif ou une veille en audio, tandis que toute la synthèse reste sur votre machine.",
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
		title: "Votre première écoute commence ici.",
		subtitle: "Choisissez votre méthode. Dans quelques minutes, votre prochaine lecture pourra quitter l’écran avec vous.",
		brewLabel: "macOS — Homebrew (ni Python ni uv requis)",
		sourceLabel: "Depuis les sources (uv)",
		pypiLabel: "pip / pipx / uv — depuis PyPI",
		note: "Installez Speekify, lancez la configuration une fois, puis transformez votre premier lien en audio. Les modèles locaux sont téléchargés et préchauffés automatiquement ; chaque écoute suivante reste prête sur votre machine.",
	},
	openSource: {
		badge: "Sous licence MIT",
		title: "Utilisez-le aujourd’hui. Façonnez la suite.",
		body: "Speekify est construit en public sous licence MIT. Inspectez chaque ligne, proposez la voix ou le workflow dont vous avez besoin et aidez l’audio local à devenir utile à davantage de personnes.",
		star: "Rejoindre le projet sur GitHub",
		report: "Signaler un problème",
	},
	faq: {
		title: "Les réponses utiles avant l’installation.",
		subtitle: "L’essentiel sur la synthèse vocale locale, les sources compatibles, la confidentialité, les voix et les intégrations IA.",
		items: [
			{
				question: "Qu’est-ce que Speekify ?",
				answer: "Speekify est un outil open source de synthèse vocale en ligne de commande. Il extrait le texte lisible depuis une saisie directe, stdin, des fichiers texte, des PDF textuels, des articles web et des transcriptions YouTube, puis crée un fichier WAV local avec Supertonic v3.",
			},
			{
				question: "Speekify envoie-t-il mes documents dans le cloud ?",
				answer: "Non. La synthèse vocale s’exécute sur votre machine et le WAV généré reste local. Lorsque vous fournissez une URL web ou YouTube, Speekify récupère cette source publique, mais n’envoie pas le texte extrait à un service vocal distant.",
			},
			{
				question: "Quels formats d’entrée et de sortie sont compatibles ?",
				answer: "Speekify accepte le texte en ligne, stdin, les fichiers .txt et .md, les PDF textuels, les URL d’articles lisibles et les transcriptions YouTube. Il produit actuellement des fichiers audio WAV standard.",
			},
			{
				question: "Quelles langues et voix sont disponibles ?",
				answer: "Speekify détecte automatiquement la langue source et prend en charge de nombreuses langues Supertonic, dont le français, l’anglais, l’allemand, l’espagnol, l’italien, le portugais, le japonais et le coréen. Dix voix intégrées sont disponibles, ainsi que des styles JSON Voice Builder personnalisés.",
			},
			{
				question: "Un assistant IA peut-il utiliser Speekify ?",
				answer: "Oui. Le serveur MCP intégré expose la génération audio locale comme outil pour les clients compatibles, notamment Claude Code, Codex et GitHub Copilot, tandis que la synthèse reste sur votre ordinateur.",
			},
			{
				question: "Comment installer Speekify ?",
				answer: "Installez le paquet autonome avec Homebrew sur macOS, ou le paquet Python avec pipx ou uv. Lancez speekify setup une fois pour télécharger et préchauffer le modèle vocal local, puis passez du texte, un fichier ou une URL à la commande speekify.",
			},
		],
	},
	footer: {
		tagline: "Vos lectures en mouvement — open source et créées en local.",
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
