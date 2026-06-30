import { useState } from "react";

interface Props {
	code: string;
	label?: string;
}

function CopyIcon() {
	return (
		<svg
			xmlns="http://www.w3.org/2000/svg"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth={2}
			strokeLinecap="round"
			strokeLinejoin="round"
			className="size-4"
			aria-hidden="true"
		>
			<rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
			<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
		</svg>
	);
}

export default function CodeBlock({ code, label }: Props) {
	const [copied, setCopied] = useState(false);

	const copy = () => {
		if (!navigator.clipboard) return;
		navigator.clipboard.writeText(code).then(() => {
			setCopied(true);
			window.setTimeout(() => setCopied(false), 2000);
		});
	};

	return (
		<>
			{label && <p className="text-muted-foreground mb-2 text-xs">{label}</p>}
			<figure className="group relative">
				<pre className="bg-card border-border text-foreground overflow-x-auto rounded-lg border p-4 font-mono text-sm"><code>{code}</code></pre>
				<button
					type="button"
					onClick={copy}
					aria-label="Copy"
					className="border-border bg-background/80 text-muted-foreground hover:text-foreground absolute top-2 right-2 rounded-md border px-2 py-1 text-xs opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100"
				>
					{copied ? "Copied" : <CopyIcon />}
				</button>
			</figure>
		</>
	);
}
