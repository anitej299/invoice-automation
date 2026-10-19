import type { ReactNode } from "react";
export function Badge({ value }: { value: string }) {
  return (
    <span className={`badge badge-${value.toLowerCase()}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}
export function Notice({
  error,
  loading,
}: {
  error?: string;
  loading?: boolean;
}) {
  return error ? (
    <div role="alert" className="notice error">
      {error}
    </div>
  ) : loading ? (
    <div role="status" className="notice">
      Loading workspace…
    </div>
  ) : null;
}
export function Empty({ children }: { children?: ReactNode }) {
  return (
    <div className="empty">{children || "No records match these filters."}</div>
  );
}
export function Pagination({
  page,
  total,
  onChange,
}: {
  page: number;
  total: number;
  onChange: (page: number) => void;
}) {
  return (
    <div className="pagination">
      <span>
        {total} records · Page {page} of {Math.max(1, Math.ceil(total / 20))}
      </span>
      <div>
        <button disabled={page === 1} onClick={() => onChange(page - 1)}>
          Previous
        </button>
        <button
          disabled={page * 20 >= total}
          onClick={() => onChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
