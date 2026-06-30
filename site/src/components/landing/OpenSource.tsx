import { MotionPreset } from "@/components/ui/motion-preset";
import { buttonVariants } from "@/components/ui/button";
import { badgeVariants } from "@/components/ui/badge";
import IconBrandGithub from "@tabler/icons-react/dist/esm/icons/IconBrandGithub.mjs";
import IconBug from "@tabler/icons-react/dist/esm/icons/IconBug.mjs";

const repo = "https://github.com/OtterlySpaceLabs/speekify";

interface OpenSourceContent {
	badge: string;
	title: string;
	body: string;
	star: string;
	report: string;
}

export default function OpenSource({ content }: { content: OpenSourceContent }) {
	return (
		<section id="open-source" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
			<div className="flex flex-col items-center text-center">
				<MotionPreset fade zoom transition={{ duration: 0.5 }}>
					<span className={badgeVariants({ variant: "secondary" })}>{content.badge}</span>
				</MotionPreset>

				<MotionPreset
					component="h2"
					className="mt-6"
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
					className="mx-auto mt-6 max-w-2xl"
					fade
					blur
					slide={{ direction: "up", offset: 40 }}
					delay={0.2}
					transition={{ duration: 0.5 }}
				>
					{content.body}
				</MotionPreset>

				<MotionPreset
					className="mt-8 flex flex-wrap items-center justify-center gap-3"
					fade
					slide={{ direction: "up", offset: 30 }}
					delay={0.3}
					transition={{ duration: 0.5 }}
				>
					<a href={repo} className={buttonVariants({ size: "lg" })}>
						<IconBrandGithub aria-hidden="true" />
						{content.star}
					</a>
					<a href={`${repo}/issues`} className={buttonVariants({ variant: "outline", size: "lg" })}>
						<IconBug aria-hidden="true" />
						{content.report}
					</a>
				</MotionPreset>
			</div>
		</section>
	);
}
