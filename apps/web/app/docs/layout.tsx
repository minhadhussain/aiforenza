import type { ReactNode } from "react";

import { DocsLayoutShell } from "@/components/docs/docs-layout-shell";
import { DocsSidebar } from "@/components/docs/docs-sidebar";

export default function DocsLayout({ children }: { children: ReactNode }) {
  return (
    <DocsLayoutShell>
      <DocsSidebar basePath="/docs" />
      <div className="min-w-0">{children}</div>
    </DocsLayoutShell>
  );
}
