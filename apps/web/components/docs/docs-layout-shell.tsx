import type { ReactNode } from "react";

import { DocsSidebar } from "@/components/docs/docs-sidebar";
import { PublicShell } from "@/components/home/public-shell";

type DocsLayoutShellProps = {
  children: ReactNode;
};

export function DocsLayoutShell({ children }: DocsLayoutShellProps) {
  return (
    <PublicShell>
      <div className="grid gap-8 lg:grid-cols-[260px_minmax(0,1fr)]">{children}</div>
    </PublicShell>
  );
}
