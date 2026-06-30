import { MotionPreset } from "@/components/ui/motion-preset";
import { buttonVariants } from "@/components/ui/button";
import { badgeVariants } from "@/components/ui/badge";
import CodeBlock from "@/components/landing/CodeBlock";
import IconBrandGithub from "@tabler/icons-react/dist/esm/icons/IconBrandGithub.mjs";

const repo = "https://github.com/OtterlySpaceLabs/speekify";
const heroCommand = 'speekify "https://example.com/article"';

interface HeroContent {
	badge: string;
	badgeText: string;
	title: string;
	description: string;
	getStarted: string;
	viewGithub: string;
	caption: string;
}

export default function Hero({ content }: { content: HeroContent }) {
	return (
		<section id="top" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
			<div className="flex flex-col items-center text-center">
				<MotionPreset fade slide={{ direction: "down", offset: 24 }} transition={{ duration: 0.5 }}>
					<div className="bg-muted border-border inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm">
						<span className={badgeVariants({ variant: "default" })}>{content.badge}</span>
						<span className="text-muted-foreground">{content.badgeText}</span>
					</div>
				</MotionPreset>

				<MotionPreset
					component="h1"
					className="mt-6 max-w-3xl text-balance"
					fade
					blur
					slide={{ direction: "up", offset: 40 }}
					delay={0.1}
					transition={{ duration: 0.5 }}
				>
					{content.title}
				</MotionPreset>

				<MotionPreset
					component="p"
					className="text-muted-foreground mx-auto mt-6 max-w-2xl text-lg"
					fade
					blur
					slide={{ direction: "up", offset: 40 }}
					delay={0.2}
					transition={{ duration: 0.5 }}
				>
					{content.description}
				</MotionPreset>

				<MotionPreset
					className="mt-8 flex flex-wrap items-center justify-center gap-3"
					fade
					slide={{ direction: "up", offset: 30 }}
					delay={0.3}
					transition={{ duration: 0.5 }}
				>
					<a href="#install" className={buttonVariants({ size: "lg" })}>
						{content.getStarted}
					</a>
					<a href={repo} className={buttonVariants({ variant: "outline", size: "lg" })}>
						<IconBrandGithub aria-hidden="true" />
						{content.viewGithub}
					</a>
				</MotionPreset>

				<MotionPreset className="mx-auto mt-10 w-full max-w-xl" fade blur delay={0.4} transition={{ duration: 0.7 }}>
					<CodeBlock code={heroCommand} />
					<p className="text-muted-foreground mt-2 text-xs">{content.caption}</p>
				</MotionPreset>
			</div>
		</section>
	);
}
