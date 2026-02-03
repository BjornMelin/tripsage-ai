import { PublicAppShell } from "@/components/providers/app-shell";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <PublicAppShell>
      <main id={MAIN_CONTENT_ID} className="min-h-screen" tabIndex={-1}>
        {children}
      </main>
    </PublicAppShell>
  );
}
