import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ExternalLink, ArrowLeft } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { api, errorMessage, money } from "../services/api";
import type { Invoice, Page, Audit } from "../types";
import { Badge, Notice } from "../components/ui";
export default function InvoiceDetails() {
  const { id } = useParams();
  const invoice = useApi<Invoice>(`/invoices/${id}`);
  const logs = useApi<Page<Audit>>(
    `/audit-logs?invoice_id=${id}&page_size=100`,
  );
  const history = useApi<
    {
      id: number;
      reminder_type: string;
      status: string;
      sent_at: string | null;
      recipient: string;
    }[]
  >(`/invoices/${id}/reminders`);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  async function action(name: string) {
    setBusy(true);
    setError("");
    try {
      await api.post(`/invoices/${id}/${name}`, { reason });
      invoice.reload();
      logs.reload();
      setReason("");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  function edit() {
    const i = invoice.data!;
    const fields = [
      "invoice_number",
      "vendor_name",
      "vendor_email",
      "vendor_address",
      "customer_name",
      "customer_address",
      "invoice_date",
      "due_date",
      "purchase_order_number",
      "currency",
      "subtotal",
      "tax",
      "discount",
      "total",
      "payment_terms",
      "confidence",
      "warnings",
    ];
    setDraft(
      JSON.stringify(
        {
          ...Object.fromEntries(fields.map((k) => [k, i[k as keyof Invoice]])),
          line_items: i.items,
        },
        null,
        2,
      ),
    );
    setEditing(true);
  }
  async function save() {
    setBusy(true);
    setError("");
    try {
      await api.patch(`/invoices/${id}`, JSON.parse(draft));
      setEditing(false);
      invoice.reload();
      logs.reload();
    } catch (e) {
      setError(
        e instanceof SyntaxError
          ? "Invalid JSON. Check the edited fields."
          : errorMessage(e),
      );
    } finally {
      setBusy(false);
    }
  }
  const i = invoice.data;
  return (
    <>
      <Link className="back" to="/invoices">
        <ArrowLeft size={15} /> All invoices
      </Link>
      <Notice error={invoice.error} loading={invoice.loading} />
      {i && (
        <>
          <div className="page-heading">
            <div>
              <p className="eyebrow">INVOICE DETAIL · #{i.id}</p>
              <h1>{i.invoice_number || "Unidentified invoice"}</h1>
              <p className="muted">
                {i.source_filename || "Manually entered"} · Received{" "}
                {new Date(i.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex gap-2">
              <Badge value={i.status} />
              <Badge value={i.risk_level} />
            </div>
          </div>
          <div className="detail-grid">
            <div>
              <section className="card document">
                <div className="section-heading">
                  <h3>Invoice summary</h3>
                  {i.google_drive_url?.startsWith(
                    "https://drive.google.com/",
                  ) && (
                    <a
                      href={i.google_drive_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Original document <ExternalLink size={14} />
                    </a>
                  )}
                </div>
                <div className="parties">
                  <div>
                    <p className="eyebrow">FROM</p>
                    <h3>{i.vendor_name || "Unknown vendor"}</h3>
                    <p>{i.vendor_email}</p>
                    <p>{i.vendor_address}</p>
                  </div>
                  <div>
                    <p className="eyebrow">BILL TO</p>
                    <h3>{i.customer_name || "—"}</h3>
                    <p>{i.customer_address}</p>
                  </div>
                </div>
                <div className="metadata">
                  {[
                    ["Invoice date", i.invoice_date],
                    ["Due date", i.due_date],
                    ["Purchase order", i.purchase_order_number],
                    ["Payment terms", i.payment_terms],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <small>{k}</small>
                      <strong>{v || "—"}</strong>
                    </div>
                  ))}
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Description</th>
                        <th>Qty</th>
                        <th>Unit price</th>
                        <th>Tax</th>
                        <th>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {i.items.map((item, n) => (
                        <tr key={n}>
                          <td>{item.description}</td>
                          <td>{item.quantity}</td>
                          <td>{money(item.unit_price, i.currency)}</td>
                          <td>{money(item.tax, i.currency)}</td>
                          <td>{money(item.amount, i.currency)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="totals">
                  {[
                    ["Subtotal", i.subtotal],
                    ["Tax", i.tax],
                    ["Discount", i.discount],
                    ["Total", i.total],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <span>{label}</span>
                      <strong>{money(value, i.currency)}</strong>
                    </div>
                  ))}
                </div>
              </section>
              <section className="card mt-5">
                <h3>Audit trail</h3>
                <Notice error={logs.error} />
                <div className="timeline">
                  {logs.data?.items.map((a) => (
                    <div key={a.id}>
                      <strong>{a.action.replaceAll("_", " ")}</strong>
                      <p>{a.description}</p>
                      <small>
                        {a.performed_by} ·{" "}
                        {new Date(a.created_at).toLocaleString()}
                      </small>
                    </div>
                  ))}
                </div>
              </section>
              <section className="card mt-5">
                <h3>Reminder history</h3>
                {history.data?.length === 0 && (
                  <p className="muted">No reminders reserved or sent.</p>
                )}
                {history.data?.map((r) => (
                  <p key={r.id}>
                    {r.reminder_type} · {r.status} · {r.recipient} ·{" "}
                    {r.sent_at || "Delivery not acknowledged"}
                  </p>
                ))}
              </section>
            </div>
            <aside>
              <section className="card">
                <h3>Review & actions</h3>
                <p className="muted">
                  Resolve validation errors before approval. Record a reason or
                  payment reference.
                </p>
                <label>
                  Decision note
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Review notes or payment reference"
                  />
                </label>
                <Notice error={error} />
                <div className="actions">
                  {["VALIDATED", "UNDER_REVIEW"].includes(i.status) && (
                    <>
                      <button
                        className="primary"
                        disabled={
                          busy ||
                          reason.length < 3 ||
                          i.validation_errors.length > 0
                        }
                        onClick={() => action("approve")}
                      >
                        Approve invoice
                      </button>
                      <button onClick={edit}>Edit extracted fields</button>
                    </>
                  )}
                  {[
                    "APPROVED",
                    "PAYMENT_PENDING",
                    "DUE_SOON",
                    "OVERDUE",
                  ].includes(i.status) && (
                    <button
                      className="primary"
                      disabled={busy || reason.length < 3}
                      onClick={() => action("pay")}
                    >
                      Mark as paid
                    </button>
                  )}
                  {!["PAID", "REJECTED", "RECEIVED", "PROCESSING"].includes(
                    i.status,
                  ) && (
                    <button
                      className="danger"
                      disabled={busy || reason.length < 3}
                      onClick={() => action("reject")}
                    >
                      Reject invoice
                    </button>
                  )}
                </div>
                {i.paid_at && (
                  <p>Paid {new Date(i.paid_at).toLocaleString()}</p>
                )}
              </section>
              <section className="card mt-5">
                <h3>Risk & validation</h3>
                {i.risk_reasons.length === 0 ? (
                  <p className="muted">All validation rules passed.</p>
                ) : (
                  <ul className="reasons">
                    {i.risk_reasons.map((r, n) => (
                      <li key={n}>{r}</li>
                    ))}
                  </ul>
                )}
                {i.validation_errors.length > 0 && (
                  <p className="error">
                    {i.validation_errors.length} blocking validation error(s)
                  </p>
                )}
              </section>
              <section className="card mt-5">
                <h3>Extraction confidence</h3>
                {Object.entries(i.confidence).map(([field, value]) => (
                  <div className="confidence" key={field}>
                    <div>
                      <span>{field.replaceAll("_", " ")}</span>
                      <strong>{Math.round(value * 100)}%</strong>
                    </div>
                    <progress max="1" value={value} />
                  </div>
                ))}
              </section>
            </aside>
          </div>
          <details className="card mt-5">
            <summary>Extracted document text</summary>
            <pre>{i.extracted_text || "No extracted text available."}</pre>
          </details>
          {editing && (
            <div
              className="modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="edit-title"
            >
              <div className="card">
                <h2 id="edit-title">Review extracted fields</h2>
                <p className="muted">
                  Edit structured fields and line items. Saving reruns all
                  validation rules.
                </p>
                <textarea
                  aria-label="Extracted invoice JSON"
                  className="json-editor"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                />
                <Notice error={error} />
                <div className="flex gap-3">
                  <button className="primary" disabled={busy} onClick={save}>
                    Save and validate
                  </button>
                  <button onClick={() => setEditing(false)}>Cancel</button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
