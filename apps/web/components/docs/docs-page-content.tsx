import type { DocPage } from "@/lib/docs";

type DocsPageContentProps = {
  page: DocPage;
};

export function DocsPageContent({ page }: DocsPageContentProps) {
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
          </section>
        ))}
      </div>
    </article>
  );
}
