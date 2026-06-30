import { MotionPreset } from "@/components/ui/motion-preset";
import { buttonVariants } from "@/components/ui/button";
import CodeBlock from "@/components/landing/CodeBlock";

// Commands are locale-agnostic; labels come from the dictionary by position (index-aligned).
const codes = [
	'speekify "Hello world"',
	'speekify "https://example.com/article"',
	"speekify ~/Documents/article.pdf",
	'speekify --lang fr "https://www.youtube.com/watch?v=eSP7PLTXNy8"',
	"printf 'Hello from stdin' | speekify",
	'speekify --voice F2 --output-dir ~/Desktop "Hello world"',
];

interface CliContent {
	title: string;
	subtitle: string;
	labels: readonly string[];
	fullRef: string;
}

export default function CliUsage({ content }: { content: CliContent }) {
	return (
		<section id="cli" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
			<div className="max-w-3xl">
				<MotionPreset component="h2" fade blur slide={{ direction: "up", offset: 40 }} transition={{ duration: 0.5 }}>
					{content.title}
				</MotionPreset>
				<MotionPreset
					component="p"
					className="text-muted-foreground mt-4 text-lg"
					fade
					blur
					slide={{ direction: "up", offset: 40 }}
					delay={0.15}
					transition={{ duration: 0.5 }}
				>
					{content.subtitle}
				</MotionPreset>
			</div>

			<div className="mt-10 grid gap-4 md:grid-cols-2">
				{codes.map((code, index) => (
					<MotionPreset
						key={index}
						fade
						blur
						slide={{ direction: "up", offset: 30 }}
						delay={0.08 * index}
						transition={{ duration: 0.5 }}
					>
						<CodeBlock label={content.labels[index]} code={code} />
					</MotionPreset>
				))}
			</div>

			<MotionPreset className="mt-6" fade slide={{ direction: "up", offset: 20 }} delay={0.2} transition={{ duration: 0.5 }}>
				<a
					href="https://github.com/OtterlySpaceLabs/speekify/blob/main/docs/usage.md"
					className={buttonVariants({ variant: "link" })}
				>
					{content.fullRef}
				</a>
			</MotionPreset>
		</section>
	);
}
