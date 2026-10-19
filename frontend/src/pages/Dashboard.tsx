import { Link } from "react-router-dom";
import { useState } from "react";
import {
  ArrowUpRight,
  ShieldCheck,
  Clock3,
  Files,
  CircleCheck,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
} from "recharts";
import { useApi } from "../hooks/useApi";
import { money } from "../services/api";
import type { Stats, Charts, Page, Invoice, Series } from "../types";
import { Badge, Notice, Empty } from "../components/ui";
function Chart({
  title,
  subtitle,
  data,
  bar = false,
}: {
  title: string;
  subtitle: string;
  data: Series;
  bar?: boolean;
}) {
  return (
    <section className="card chart">
      <h3>{title}</h3>
      <p className="muted">{subtitle}</p>
      <div style={{ height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          {bar ? (
            <BarChart data={data}>
              <CartesianGrid vertical={false} stroke="#edf0ee" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10 }}
                tickFormatter={(v) => String(v).replaceAll("_", " ")}
              />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar
                dataKey="value"
                fill="#2f7771"
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          ) : (
            <AreaChart data={data}>
              <defs>
                <linearGradient
                  id={title.replaceAll(" ", "")}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="0%" stopColor="#4a9585" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#4a9585" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="#edf0ee" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area
                isAnimationActive={false}
                type="monotone"
                dataKey="value"
                stroke="#2f7771"
                fill={`url(#${title.replaceAll(" ", "")})`}
                strokeWidth={2}
              />
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>
    </section>
  );
}
export default function Dashboard() {
  const stats = useApi<Stats>("/dashboard/stats");
  const [currency, setCurrency] = useState("INR");
  const charts = useApi<Charts>(
    `/dashboard/charts?currency=${encodeURIComponent(currency)}`,
  );
  const review = useApi<Page<Invoice>>(
    "/invoices?status=UNDER_REVIEW&page_size=5",
  );
  const s = stats.data;
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE OVERVIEW</p>
          <h1>Every invoice. In focus.</h1>
          <p className="muted">
            A clear view of your payables and what needs attention.
          </p>
        </div>
        <Link className="primary" to="/invoices">
          View invoices <ArrowUpRight size={17} />
        </Link>
      </div>
      <Notice error={stats.error || charts.error} loading={stats.loading} />
      {s && (
        <>
          <div className="kpis">
            {[
              [Files, "Total invoices", s.total_invoices],
              [Clock3, "Awaiting payment", s.pending],
              [ShieldCheck, "High risk", s.high_risk],
              [CircleCheck, "Paid invoices", s.paid],
            ].map(([Icon, label, value]) => {
              const Component = Icon as typeof Files;
              return (
                <section className="card kpi" key={String(label)}>
                  <div>
                    <span>{String(label)}</span>
                    <Component size={18} />
                  </div>
                  <strong>{String(value).padStart(2, "0")}</strong>
                  <small>
                    {label === "Awaiting payment"
                      ? `${s.due_soon} due soon · ${s.overdue} overdue`
                      : "Across your workspace"}
                  </small>
                </section>
              );
            })}
          </div>
          <div className="balance-strip">
            <div>
              <span className="eyebrow">OUTSTANDING BALANCE</span>
              <h2>
                {money(
                  s.amounts_by_currency[currency]?.outstanding ?? 0,
                  currency,
                )}
              </h2>
            </div>
            <div>
              <span>Total invoice value</span>
              <strong>
                {money(s.amounts_by_currency[currency]?.total ?? 0, currency)}
              </strong>
            </div>
            <label>
              Currency
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
              >
                {Array.from(
                  new Set(["INR", ...Object.keys(s.amounts_by_currency)]),
                ).map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
          </div>
        </>
      )}
      {charts.data && (
        <div className="charts">
          <Chart
            title="Invoice value"
            subtitle={`Monthly volume · ${currency}`}
            data={charts.data.monthly_value}
          />
          <Chart
            title="Invoice status"
            subtitle="Where invoices stand today"
            data={charts.data.by_status}
            bar
          />
          <Chart
            title="Risk distribution"
            subtitle="Deterministic validation results"
            data={charts.data.by_risk}
            bar
          />
          <Chart
            title="Overdue balance"
            subtitle={`30-day reconstruction · ${currency}`}
            data={charts.data.overdue_trend}
          />
          <Chart
            title="Vendor spending"
            subtitle={`Top vendors by invoice value · ${currency}`}
            data={charts.data.vendor_spending}
            bar
          />
          <Chart
            title="Processing volume"
            subtitle="Invoices received per day"
            data={charts.data.processing_trend}
          />
        </div>
      )}
      <section className="card">
        <div className="section-heading">
          <div>
            <h3>Needs your attention</h3>
            <p className="muted">Review exceptions before approving payment.</p>
          </div>
          <Link to="/invoices?status=UNDER_REVIEW">View queue →</Link>
        </div>
        <Notice error={review.error} />
        {review.data?.items.map((i) => (
          <Link className="review-row" key={i.id} to={`/invoices/${i.id}`}>
            <div className="vendor-avatar">
              {i.vendor_name?.slice(0, 2).toUpperCase() || "?"}
            </div>
            <div>
              <strong>{i.vendor_name || "Unknown vendor"}</strong>
              <small>{i.invoice_number || "Unidentified invoice"}</small>
            </div>
            <Badge value={i.risk_level} />
            <span className="ml-auto">{money(i.total, i.currency)}</span>
            <ArrowUpRight size={18} />
          </Link>
        ))}
        {review.data?.items.length === 0 && (
          <Empty>You're all caught up. No invoices awaiting review.</Empty>
        )}
      </section>
    </>
  );
}
