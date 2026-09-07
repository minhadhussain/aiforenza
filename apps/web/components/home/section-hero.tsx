type SectionHeroProps = {
  eyebrow: string;
  title: string;
  copy: string;
};

export function SectionHero({ eyebrow, title, copy }: SectionHeroProps) {
  return (
    <section className="relative overflow-hidden rounded-[2.25rem] border border-white/6 px-6 py-20 sm:px-10 lg:px-16">
      <div className="pointer-events-none absolute inset-0 opacity-70">
        <div className="absolute left-1/2 top-[18%] h-[300px] w-[300px] -translate-x-1/2 rounded-full bg-white/[0.05] blur-[120px]" />
        <div className="absolute left-[16%] top-[28%] h-32 w-px bg-gradient-to-b from-transparent via-white/14 to-transparent" />
        <div className="absolute right-[16%] top-[34%] h-32 w-px bg-gradient-to-b from-transparent via-white/14 to-transparent" />
        <div className="absolute left-1/2 top-[46%] h-px w-[46%] -translate-x-1/2 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      </div>

      <div className="relative z-10 mx-auto max-w-4xl text-center">
        <p className="text-sm uppercase tracking-[0.24em] text-[var(--muted)]">{eyebrow}</p>
        <h1 className="mt-6 font-[family-name:var(--font-heading)] text-[2.8rem] leading-[0.95] tracking-[-0.05em] text-white sm:text-[4.2rem] lg:text-[5.25rem]">
          {title}
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-[var(--muted)] sm:text-lg">{copy}</p>
      </div>
    </section>
  );
}
