/**
 * @fileoverview Minimal OAuth provider icons to avoid shipping large icon packs.
 */

import type { ComponentProps } from "react";

type SvgIconProps = ComponentProps<"svg">;

export function GitHubMarkIcon(props: SvgIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" role="img" {...props}>
      <title>GitHub</title>
      <path d="M12 2C6.48 2 2 6.58 2 12.26c0 4.54 2.87 8.4 6.84 9.76.5.1.68-.22.68-.48 0-.24-.01-.86-.01-1.68-2.78.62-3.37-1.39-3.37-1.39-.45-1.2-1.11-1.52-1.11-1.52-.91-.64.07-.63.07-.63 1.01.07 1.54 1.07 1.54 1.07.9 1.6 2.36 1.14 2.94.87.09-.67.35-1.14.63-1.4-2.22-.26-4.55-1.15-4.55-5.12 0-1.13.39-2.05 1.03-2.77-.1-.26-.45-1.3.1-2.71 0 0 .84-.28 2.75 1.06A9.1 9.1 0 0 1 12 6.9c.85 0 1.7.12 2.5.36 1.91-1.34 2.75-1.06 2.75-1.06.55 1.41.2 2.45.1 2.71.64.72 1.03 1.64 1.03 2.77 0 3.98-2.34 4.86-4.57 5.12.36.32.68.96.68 1.94 0 1.4-.01 2.52-.01 2.86 0 .26.18.58.69.48A10.27 10.27 0 0 0 22 12.26C22 6.58 17.52 2 12 2z" />
    </svg>
  );
}

export function GoogleGIcon(props: SvgIconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" role="img" {...props}>
      <title>Google</title>
      <path d="M12.24 10.29v3.41h5.79c-.23 1.46-1.67 4.28-5.79 4.28-3.48 0-6.32-2.89-6.32-6.45s2.84-6.45 6.32-6.45c1.98 0 3.3.84 4.06 1.56l2.77-2.67C17.3 6.28 15.02 5 12.24 5 7.69 5 4 8.75 4 12.53S7.69 20.06 12.24 20.06c5.39 0 8.97-3.79 8.97-9.12 0-.61-.07-1.08-.15-1.55H12.24z" />
    </svg>
  );
}
