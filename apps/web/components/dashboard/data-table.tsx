import type { ReactNode } from "react";

type Column<T> = {
  key: string;
  label: string;
  render: (item: T) => ReactNode;
};

type DataTableProps<T> = {
  title: string;
  description: string;
  columns: Array<Column<T>>;
  rows: T[];
  emptyMessage: string;
};

export function DataTable<T>({ title, description, columns, rows, emptyMessage }: DataTableProps<T>) {
  return (
    <section className="rounded-[1.9rem] border border-white/8 bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur">
      <div className="mb-6">
        <p className="text-sm uppercase tracking-[0.18em] text-[var(--muted)]">{title}</p>
        <h2 className="mt-3 font-[family-name:var(--font-heading)] text-2xl text-white">{title}</h2>
        <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{description}</p>
      </div>

      {rows.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-3 text-left text-sm">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column.key} className="px-4 py-2 font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index} className="rounded-[1.25rem] bg-[var(--surface-strong)] transition hover:bg-white/[0.04]">
                  {columns.map((column) => (
                    <td key={column.key} className="px-4 py-4 align-top text-[var(--text)] first:rounded-l-[1.25rem] last:rounded-r-[1.25rem]">
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
          <div className="rounded-[1.25rem] border border-white/8 bg-[var(--surface-strong)] p-4 text-sm leading-6 text-[var(--muted)]">
            {emptyMessage}
          </div>
      )}
    </section>
  );
}
