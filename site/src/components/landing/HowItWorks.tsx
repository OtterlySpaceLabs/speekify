import { MotionPreset } from "@/components/ui/motion-preset";

interface HowContent {
	title: string;
	steps: readonly { title: string; body: string }[];
}

export default function HowItWorks({ content }: { content: HowContent }) {
	return (
		<section id="how" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
			<div className="max-w-3xl">
				<MotionPreset component="h2" fade blur slide={{ direction: "up", offset: 40 }} transition={{ duration: 0.5 }}>
					{content.title}
				</MotionPreset>
			</div>

			<ol className="mt-10 flex flex-col gap-6">
				{content.steps.map((step, index) => (
					<MotionPreset
						key={step.title}
						component="li"
						className="flex items-start gap-4"
						fade
						blur
						slide={{ direction: "up", offset: 40 }}
						delay={0.12 * index}
						transition={{ duration: 0.5 }}
					>
						<span className="bg-primary text-primary-foreground flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold">
							{index + 1}
						</span>
						<div>
							<div className="text-foreground text-base font-semibold">{step.title}</div>
							{/* step.body carries authored <code> markup from the i18n dictionary */}
							<p
								className="text-muted-foreground mt-1 text-sm leading-relaxed"
								dangerouslySetInnerHTML={{ __html: step.body }}
							/>
						</div>
					</MotionPreset>
				))}
			</ol>
		</section>
	);
}
