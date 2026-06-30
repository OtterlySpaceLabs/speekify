import { MotionPreset } from "@/components/ui/motion-preset";
import IconFileImport from "@tabler/icons-react/dist/esm/icons/IconFileImport.mjs";
import IconCpu from "@tabler/icons-react/dist/esm/icons/IconCpu.mjs";
import IconLanguage from "@tabler/icons-react/dist/esm/icons/IconLanguage.mjs";
import IconMicrophone2 from "@tabler/icons-react/dist/esm/icons/IconMicrophone2.mjs";
import IconPlugConnected from "@tabler/icons-react/dist/esm/icons/IconPlugConnected.mjs";
import IconBrandGithub from "@tabler/icons-react/dist/esm/icons/IconBrandGithub.mjs";

interface WhatContent {
	title: string;
	subtitle: string;
	cards: readonly { title: string; body: string }[];
}

// Icons map to cards by position; content text comes from i18n via props.
const icons = [IconFileImport, IconCpu, IconLanguage, IconMicrophone2, IconPlugConnected, IconBrandGithub];

export default function What({ content }: { content: WhatContent }) {
	return (
		<section id="what" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
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

			<div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{content.cards.map((card, index) => {
					const Icon = icons[index] ?? icons[0];
					return (
						<MotionPreset
							key={card.title}
							fade
							blur
							slide={{ direction: "up", offset: 40 }}
							delay={0.2 + index * 0.1}
							transition={{ duration: 0.6 }}
						>
							<div className="bg-card border-border h-full rounded-xl border p-6">
								<Icon className="text-primary mb-3 size-6" stroke={1.5} aria-hidden="true" />
								<div className="text-foreground mb-2 text-base font-semibold">{card.title}</div>
								<div className="text-muted-foreground text-sm leading-relaxed">{card.body}</div>
							</div>
						</MotionPreset>
					);
				})}
			</div>
		</section>
	);
}
