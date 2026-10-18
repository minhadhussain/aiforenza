import Link from "next/link";

import type { DocPage } from "@/lib/docs";
import { OpenCodeSetup } from "@/components/docs/opencode-setup";

type DocsPageContentProps = {
  page: DocPage;
  basePath?: string;
};

export function DocsPageContent({ page, basePath = "/docs" }: DocsPageContentProps) {
  return (
    <article className="space-y-8">
      <header className="border border-white/8 bg-white/[0.025] px-6 py-10 shadow-[var(--shadow)]">
        <p className="text-sm uppercase tracking-[0.18em] text-[var(--muted)]">Documentation</p>
        <h1 className="mt-5 font-[family-name:var(--font-heading)] text-4xl tracking-[-0.04em] text-white sm:text-5xl">{page.title}</h1>
        <p className="mt-5 max-w-3xl text-base leading-8 text-[var(--muted)]">{page.summary}</p>
      </header>

      <div className="space-y-5">
        {page.sections.map((section) => (
          <section key={section.heading} className="border border-white/8 bg-white/[0.025] px-6 py-6 shadow-[var(--shadow)]">
            <h2 className="text-xl font-semibold text-white">{section.heading}</h2>
            <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{section.body}</p>
            {section.widget === "opencode-setup" && <OpenCodeSetup />}
            {section.widget === "opencode-quickstart" && <OpenCodeSetup compact />}

            {section.bullets?.length ? (
              <ul className="mt-4 space-y-3 text-sm leading-7 text-[var(--muted)]">
                {section.bullets.map((bullet) => (
                  <li key={bullet}>- {bullet}</li>
                ))}
              </ul>
            ) : null}

            {section.code ? (
              <pre className="mt-5 overflow-x-auto border border-white/10 bg-[#090b0d] px-4 py-4 text-sm leading-7 text-[#edf1f7]">{section.code}</pre>
            ) : null}
            {section.links?.length ? (
              <div className="mt-5 flex flex-wrap gap-3">
                {section.links.map((link) => (
                  <Link key={link.label} href={"slug" in link ? `${basePath}/${link.slug}` : link.href} className="border border-white/20 bg-white/[0.04] px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/[0.08]">{link.label} →</Link>
                ))}
              </div>
            ) : null}
          </section>
        ))}
      </div>
    </article>
  );
}
