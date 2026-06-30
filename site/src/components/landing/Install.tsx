import { MotionPreset } from "@/components/ui/motion-preset";
import CodeBlock from "@/components/landing/CodeBlock";

const brewCommand = `brew tap otterlyspacelabs/speekify https://github.com/OtterlySpaceLabs/speekify
brew install speekify
speekify setup`;

const sourceCommand = `uv sync
uv run speekify setup`;

const pypiCommand = `pip install speekify        # or: pipx install speekify
uv tool install speekify    # uv users
speekify setup`;

interface InstallContent {
	title: string;
	subtitle: string;
	brewLabel: string;
	sourceLabel: string;
	pypiLabel: string;
	note: string;
}

export default function Install({ content }: { content: InstallContent }) {
	return (
		<section id="install" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
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

			<div className="mx-auto mt-10 flex max-w-2xl flex-col gap-6">
				<MotionPreset fade blur slide={{ direction: "up", offset: 30 }} delay={0.1} transition={{ duration: 0.5 }}>
					<CodeBlock label={content.brewLabel} code={brewCommand} />
				</MotionPreset>
				<MotionPreset fade blur slide={{ direction: "up", offset: 30 }} delay={0.2} transition={{ duration: 0.5 }}>
					<CodeBlock label={content.sourceLabel} code={sourceCommand} />
				</MotionPreset>
				<MotionPreset fade blur slide={{ direction: "up", offset: 30 }} delay={0.3} transition={{ duration: 0.5 }}>
					<CodeBlock label={content.pypiLabel} code={pypiCommand} />
				</MotionPreset>
			</div>

			<MotionPreset
				component="p"
				className="text-muted-foreground mx-auto mt-6 max-w-2xl text-sm"
				fade
				delay={0.3}
				transition={{ duration: 0.5 }}
			>
				{content.note}
			</MotionPreset>
		</section>
	);
}
