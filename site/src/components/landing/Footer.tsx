import { MotionPreset } from "@/components/ui/motion-preset";

const repo = "https://github.com/OtterlySpaceLabs/speekify";
const hrefs = [repo, `${repo}#readme`, `${repo}/blob/main/docs/usage.md`, `${repo}/blob/main/docs/mcp-clients.md`];

interface FooterContent {
	tagline: string;
	links: readonly string[];
	license: string;
	disclaimer: string;
}

export default function Footer({ content }: { content: FooterContent }) {
	const links = hrefs.map((href, index) => ({ href, label: content.links[index] }));

	return (
		<MotionPreset
			component="footer"
			className="border-border border-t"
			fade
			slide={{ direction: "up", offset: 30 }}
			transition={{ duration: 0.6 }}
		>
			<div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
				<div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
					<div>
						<div className="text-lg font-semibold">Speekify</div>
						<p className="text-muted-foreground mt-2 text-sm">{content.tagline}</p>
					</div>

					<nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
						{links.map((link) => (
							<a key={link.href} href={link.href} className="text-muted-foreground hover:text-foreground transition">
								{link.label}
							</a>
						))}
					</nav>
				</div>

				<div className="border-border mt-8 border-t pt-6">
					<p className="text-muted-foreground text-sm">{content.license}</p>
					<p className="text-muted-foreground mt-2 max-w-3xl text-xs">{content.disclaimer}</p>
				</div>
			</div>
		</MotionPreset>
	);
}
