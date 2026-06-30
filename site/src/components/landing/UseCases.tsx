import { MotionPreset } from "@/components/ui/motion-preset";
import IconArticle from "@tabler/icons-react/dist/esm/icons/IconArticle.mjs";
import IconFileTypePdf from "@tabler/icons-react/dist/esm/icons/IconFileTypePdf.mjs";
import IconBrandYoutube from "@tabler/icons-react/dist/esm/icons/IconBrandYoutube.mjs";
import IconNews from "@tabler/icons-react/dist/esm/icons/IconNews.mjs";
import IconRobot from "@tabler/icons-react/dist/esm/icons/IconRobot.mjs";

interface UseCasesContent {
	title: string;
	cases: readonly { title: string; body: string }[];
}

// Icons map to cases by position; content text comes from i18n via props.
const icons = [IconArticle, IconFileTypePdf, IconBrandYoutube, IconNews, IconRobot];

export default function UseCases({ content }: { content: UseCasesContent }) {
	return (
		<section id="use-cases" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
			<div className="max-w-3xl">
				<MotionPreset component="h2" fade blur slide={{ direction: "up", offset: 40 }} transition={{ duration: 0.5 }}>
					{content.title}
				</MotionPreset>
			</div>

			{/* Bento: first tile spans two columns on large screens for varied rhythm. */}
			<div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{content.cases.map((useCase, index) => {
					const Icon = icons[index] ?? icons[0];
					const wide = index === 0;
					return (
						<MotionPreset
							key={useCase.title}
							className={wide ? "lg:col-span-2" : undefined}
							fade
							blur
							slide={{ direction: "up", offset: 40 }}
							delay={0.2 + index * 0.1}
							transition={{ duration: 0.6 }}
						>
							<div className="bg-card border-border flex h-full flex-col rounded-xl border p-6">
								<Icon className={`text-primary mb-3 ${wide ? "size-8" : "size-6"}`} stroke={1.5} aria-hidden="true" />
								<div className={`text-foreground mb-2 font-semibold ${wide ? "text-lg" : "text-base"}`}>
									{useCase.title}
								</div>
								<div className="text-muted-foreground text-sm leading-relaxed">{useCase.body}</div>
							</div>
						</MotionPreset>
					);
				})}
			</div>
		</section>
	);
}
