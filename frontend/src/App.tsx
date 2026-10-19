import {
  BrowserRouter,
  NavLink,
  Navigate,
  Outlet,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import {
  Layers3,
  LayoutDashboard,
  Files,
  Users,
  History,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import Login from "./pages/Login";
import { lazy, Suspense } from "react";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Invoices = lazy(() => import("./pages/Invoices"));
const InvoiceDetails = lazy(() => import("./pages/InvoiceDetails"));
const Directory = lazy(() => import("./pages/Directory"));
function Shell() {
  const navigate = useNavigate();
  if (!sessionStorage.getItem("token")) return <Navigate to="/login" replace />;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <LinkBrand />
        <p className="nav-caption">WORKSPACE</p>
        <nav>
          {[
            ["/", "Overview", LayoutDashboard],
            ["/invoices", "Invoices", Files],
            ["/vendors", "Vendors", Users],
            ["/audit", "Audit logs", History],
          ].map(([path, label, Icon]) => {
            const Component = Icon as typeof Files;
            return (
              <NavLink key={String(path)} to={String(path)} end={path === "/"}>
                <Component size={18} />
                {String(label)}
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <ShieldCheck size={20} />
          <p>
            Clarity at every step.<small>Invoice operations workspace</small>
          </p>
        </div>
        <button
          className="logout"
          onClick={() => {
            sessionStorage.removeItem("token");
            navigate("/login");
          }}
        >
          <LogOut size={16} /> Sign out
        </button>
      </aside>
      <div className="workspace">
        <header>
          <span>
            Finance operations <span className="muted">/ Workspace</span>
          </span>
          <div>
            <span className="live-dot" /> Connected workspace{" "}
            <span className="user-avatar">FA</span>
          </div>
        </header>
        <main>
          <Suspense
            fallback={
              <div role="status" className="notice">
                Loading workspace…
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </main>
        <footer>
          LEDGER / INTELLIGENT INVOICE OPERATIONS{" "}
          <span>Built for a clearer financial picture.</span>
        </footer>
      </div>
    </div>
  );
}
function LinkBrand() {
  return (
    <div className="brand">
      <Layers3 size={28} /> ledger<span className="brand-dot">.</span>
    </div>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Shell />}>
          <Route index element={<Dashboard />} />
          <Route path="invoices" element={<Invoices />} />
          <Route path="invoices/:id" element={<InvoiceDetails />} />
          <Route path="vendors" element={<Directory />} />
          <Route path="audit" element={<Directory audit />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
