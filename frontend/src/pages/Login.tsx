import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, Layers3 } from "lucide-react";
import { api, errorMessage } from "../services/api";
export default function Login() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(e.currentTarget);
    try {
      const { data } = await api.post("/auth/login", {
        email: form.get("email"),
        password: form.get("password"),
      });
      sessionStorage.setItem("token", data.access_token);
      navigate("/");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login">
      <section className="login-story">
        <div className="brand">
          <Layers3 /> ledger<span> / finance operations</span>
        </div>
        <div>
          <p className="eyebrow">LESS ADMIN. MORE CLARITY.</p>
          <h1>
            From invoice
            <br />
            to insight.
          </h1>
          <p>
            One place to review invoices, understand risk,
            <br />
            and keep every payment on track.
          </p>
        </div>
        <small>INTELLIGENT INVOICE PROCESSING & PAYMENT AUTOMATION</small>
      </section>
      <section className="login-form">
        <p className="eyebrow">YOUR FINANCE WORKSPACE</p>
        <h2>Welcome back.</h2>
        <p className="muted">Sign in with your configured finance account.</p>
        <form onSubmit={submit}>
          <label>
            Email address
            <input name="email" type="email" autoComplete="username" required />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in to workspace"}
            <ArrowUpRight size={18} />
          </button>
        </form>
        <small className="muted">
          Account access is managed by your workspace administrator.
        </small>
      </section>
    </div>
  );
}
