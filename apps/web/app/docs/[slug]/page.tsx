import { notFound } from "next/navigation";

import { DocsPageContent } from "@/components/docs/docs-page-content";
import { docsPageMap, docsPages } from "@/lib/docs";

export function generateStaticParams() {
  return docsPages.map((page) => ({ slug: page.slug }));
}

export default async function DocsDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = docsPageMap[slug];

  if (!page) {
    notFound();
  }

  return <DocsPageContent page={page} />;
}
