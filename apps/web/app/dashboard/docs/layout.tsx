import type { ReactNode } from "react";

import { DocsSidebar } from "@/components/docs/docs-sidebar";

export default function DashboardDocsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid gap-8 lg:grid-cols-[260px_minmax(0,1fr)]">
      <DocsSidebar basePath="/dashboard/docs" />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
