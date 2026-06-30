// Per-icon deep imports avoid loading @tabler/icons-react's 6149-export barrel
// (build-perf warning). The package ships no per-icon .d.ts, so type the deep
// path here.
// ponytail: coupled to tabler v3 dist layout (dist/esm/icons/*.mjs); revisit on a major bump.
declare module "@tabler/icons-react/dist/esm/icons/*" {
	import type { FC, SVGProps } from "react";
	const Icon: FC<SVGProps<SVGSVGElement> & { size?: string | number; stroke?: string | number; title?: string }>;
	export default Icon;
}
