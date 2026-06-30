import { MotionPreset } from "@/components/ui/motion-preset";
import { buttonVariants } from "@/components/ui/button";
import CodeBlock from "@/components/landing/CodeBlock";

const startServer = `speekify mcp                              # stdio — for local desktop AI clients
speekify mcp --transport streamable-http  # local HTTP endpoint`;

const addToClaude = "claude mcp add --transport stdio speekify -- speekify mcp";

interface McpContent {
	title: string;
	subtitle: string;
	body: string;
	startLabel: string;
	addLabel: string;
	perClient: string;
}

export default function Mcp({ content }: { content: McpContent }) {
	return (
		<section id="mcp" className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
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

			<div className="mt-10 grid gap-4 md:grid-cols-2">
				<MotionPreset fade blur slide={{ direction: "up", offset: 30 }} delay={0.1} transition={{ duration: 0.5 }}>
					<CodeBlock label={content.startLabel} code={startServer} />
				</MotionPreset>
				<MotionPreset fade blur slide={{ direction: "up", offset: 30 }} delay={0.2} transition={{ duration: 0.5 }}>
					<CodeBlock label={content.addLabel} code={addToClaude} />
				</MotionPreset>
			</div>

			<MotionPreset className="mt-6" fade slide={{ direction: "up", offset: 20 }} delay={0.3} transition={{ duration: 0.5 }}>
				<a
					href="https://github.com/OtterlySpaceLabs/speekify/blob/main/docs/mcp-clients.md"
					className={buttonVariants({ variant: "link" })}
				>
					{content.perClient}
				</a>
			</MotionPreset>
		</section>
	);
}
