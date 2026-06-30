import { MotionPreset } from "@/components/ui/motion-preset";
import IconHeadphones from "@tabler/icons-react/dist/esm/icons/IconHeadphones.mjs";
import IconLock from "@tabler/icons-react/dist/esm/icons/IconLock.mjs";
import IconTerminal2 from "@tabler/icons-react/dist/esm/icons/IconTerminal2.mjs";

interface WhyContent {
	title: string;
	subtitle: string;
	body: string;
	cards: readonly { title: string; body: string }[];
}

// Icons map to cards by position; content text comes from i18n via props.
const icons = [IconHeadphones, IconLock, IconTerminal2];

export default function Why({ content }: { content: WhyContent }) {
	return (
		<section id="why" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
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
				<MotionPreset
					component="p"
					className="mt-6"
					fade
					blur
					slide={{ direction: "up", offset: 40 }}
					delay={0.25}
					transition={{ duration: 0.5 }}
				>
					{content.body}
				</MotionPreset>
			</div>

			<div className="mt-10 grid gap-4 sm:grid-cols-3">
				{content.cards.map((card, index) => {
					const Icon = icons[index] ?? icons[0];
					return (
						<MotionPreset
							key={card.title}
							fade
							blur
							slide={{ direction: "up", offset: 40 }}
							delay={0.3 + index * 0.15}
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
