import { useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Upload, ArrowUpRight, Search } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { api, errorMessage, money } from "../services/api";
import type { Invoice, Page } from "../types";
import { Badge, Empty, Notice, Pagination } from "../components/ui";
export default function Invoices() {
  const [params, setParams] = useSearchParams();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const page = Number(params.get("page") || 1);
  const result = useApi<Page<Invoice>>(`/invoices?${params}`);
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params);
    value ? next.set(key, value) : next.delete(key);
    next.set("page", "1");
    setParams(next);
  }
  async function upload(files: FileList | null) {
    if (!files) return;
    setBusy(true);
    setUploadError("");
    const errors = [];
    for (const file of Array.from(files)) {
      const data = new FormData();
      data.append("file", file);
      try {
        await api.post("/processing/invoice", data);
      } catch (e) {
        errors.push(`${file.name}: ${errorMessage(e)}`);
      }
    }
    setUploadError(errors.join("; "));
    setBusy(false);
    result.reload();
    if (input.current) input.current.value = "";
  }
  function sort(field: string) {
    const next = new URLSearchParams(params);
    next.set("sort", field);
    next.set(
      "direction",
      params.get("sort") === field && params.get("direction") === "asc"
        ? "desc"
        : "asc",
    );
    setParams(next);
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">PAYABLES WORKSPACE</p>
          <h1>Invoices</h1>
          <p className="muted">
            From first receipt to final payment, all in one place.
          </p>
        </div>
        <input
          aria-label="Upload invoices"
          ref={input}
          hidden
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          multiple
          onChange={(e) => upload(e.target.files)}
        />
        <button
          className="primary"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          <Upload size={17} />
          {busy ? "Processing invoices…" : "Upload invoice"}
        </button>
      </div>
      <section className="card table-card">
        <div className="filters">
          <label className="search">
            <Search size={16} />
            <input
              aria-label="Search invoices"
              placeholder="Search invoice or vendor…"
              value={params.get("q") || ""}
              onChange={(e) => filter("q", e.target.value)}
            />
          </label>
          <select
            aria-label="Status"
            value={params.get("status") || ""}
            onChange={(e) => filter("status", e.target.value)}
          >
            <option value="">All statuses</option>
            {[
              "RECEIVED",
              "PROCESSING",
              "VALIDATED",
              "UNDER_REVIEW",
              "APPROVED",
              "PAYMENT_PENDING",
              "DUE_SOON",
              "OVERDUE",
              "PAID",
              "REJECTED",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            aria-label="Risk"
            value={params.get("risk") || ""}
            onChange={(e) => filter("risk", e.target.value)}
          >
            <option value="">All risk levels</option>
            {["LOW", "MEDIUM", "HIGH"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <button onClick={() => setParams({})}>Clear filters</button>
        </div>
        <details className="advanced">
          <summary>More filters</summary>
          <div className="filters">
            {[
              ["vendor", "Vendor", "text"],
              ["date_from", "From date", "date"],
              ["date_to", "To date", "date"],
              ["amount_min", "Minimum amount", "number"],
              ["amount_max", "Maximum amount", "number"],
            ].map(([key, label, type]) => (
              <label key={key}>
                {label}
                <input
                  type={type}
                  value={params.get(key) || ""}
                  onChange={(e) => filter(key, e.target.value)}
                />
              </label>
            ))}
          </div>
        </details>
        <Notice error={uploadError || result.error} loading={result.loading} />
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {[
                  ["invoice_number", "Invoice"],
                  ["vendor_name", "Vendor"],
                  ["invoice_date", "Invoice date"],
                  ["due_date", "Due date"],
                  ["total", "Amount"],
                  ["status", "Status"],
                  ["risk_level", "Risk"],
                ].map(([field, label]) => (
                  <th key={field}>
                    <button onClick={() => sort(field)}>{label} ↕</button>
                  </th>
                ))}
                <th />
              </tr>
            </thead>
            <tbody>
              {result.data?.items.map((i) => (
                <tr key={i.id}>
                  <td>
                    <Link className="invoice-link" to={`/invoices/${i.id}`}>
                      {i.invoice_number || `#${i.id}`}
                    </Link>
                  </td>
                  <td>{i.vendor_name || "Unknown vendor"}</td>
                  <td>{i.invoice_date || "—"}</td>
                  <td>{i.due_date || "—"}</td>
                  <td className="amount">{money(i.total, i.currency)}</td>
                  <td>
                    <Badge value={i.status} />
                  </td>
                  <td>
                    <Badge value={i.risk_level} />
                  </td>
                  <td>
                    <Link
                      aria-label={`Open invoice ${i.invoice_number || i.id}`}
                      to={`/invoices/${i.id}`}
                    >
                      <ArrowUpRight size={17} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {result.data?.items.length === 0 && <Empty />}
        <Pagination
          page={page}
          total={result.data?.total || 0}
          onChange={(p) => {
            const next = new URLSearchParams(params);
            next.set("page", String(p));
            setParams(next);
          }}
        />
      </section>
    </>
  );
}
