import { useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import type { Page, Vendor, Audit } from "../types";
import { Empty, Notice, Pagination } from "../components/ui";
export default function Directory({ audit = false }: { audit?: boolean }) {
  const [page, setPage] = useState(1);
  const result = useApi<Page<Vendor & Audit>>(
    `/${audit ? "audit-logs" : "vendors"}?page=${page}`,
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            {audit ? "ACCOUNTABILITY, BUILT IN" : "YOUR BUSINESS NETWORK"}
          </p>
          <h1>{audit ? "Audit logs" : "Vendors"}</h1>
          <p className="muted">
            {audit
              ? "A traceable record of every important invoice action."
              : "Vendor information captured from your invoices."}
          </p>
        </div>
      </div>
      <section className="card table-card">
        <Notice error={result.error} loading={result.loading} />
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {(audit
                  ? ["Action", "Invoice", "Description", "Performed by", "Time"]
                  : ["Vendor", "Email", "Address"]
                ).map((v) => (
                  <th key={v}>{v}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.data?.items.map((r) => (
                <tr key={r.id}>
                  {audit ? (
                    <>
                      <td>{r.action.replaceAll("_", " ")}</td>
                      <td>
                        <Link to={`/invoices/${r.invoice_id}`}>
                          #{r.invoice_id}
                        </Link>
                      </td>
                      <td>{r.description}</td>
                      <td>{r.performed_by}</td>
                      <td>{new Date(r.created_at).toLocaleString()}</td>
                    </>
                  ) : (
                    <>
                      <td>
                        <strong>{r.name}</strong>
                      </td>
                      <td>{r.email || "—"}</td>
                      <td>{r.address || "—"}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {result.data?.items.length === 0 && <Empty />}
        <Pagination
          page={page}
          total={result.data?.total || 0}
          onChange={setPage}
        />
      </section>
    </>
  );
}
