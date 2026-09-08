import Link from "next/link";

import { DocsPageContent } from "@/components/docs/docs-page-content";
import { docsPageMap, docsPages } from "@/lib/docs";

const quickstart = docsPageMap["quickstart"];

export default function DashboardDocsPage() {
  return (
    <div className="space-y-8">
      <DocsPageContent page={quickstart} />

      <section className="border border-white/8 bg-white/[0.025] px-6 py-6 shadow-[var(--shadow)]">
        <h2 className="text-xl font-semibold text-white">All documentation</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {docsPages.map((page) => (
            <Link
              key={page.slug}
              href={`/dashboard/docs/${page.slug}`}
              className="border border-white/8 bg-white/[0.03] px-4 py-4 transition hover:bg-white/[0.05]"
            >
              <div className="text-sm font-semibold text-white">{page.title}</div>
              <div className="mt-3 text-sm leading-6 text-[var(--muted)]">{page.summary}</div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
