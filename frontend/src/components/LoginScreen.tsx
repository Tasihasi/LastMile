import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

export function LoginScreen() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [role, setRole] = useState<"biker" | "planner">("biker");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError("Please enter a username.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await login(username.trim(), role);
    } catch {
      setError("Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-header">
          <div className="app-logo">
            <svg viewBox="0 0 24 24">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 110-5 2.5 2.5 0 010 5z" />
            </svg>
          </div>
          <h1>Route Planner</h1>
          <p className="login-subtitle">Sign in to plan and view delivery routes</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="setting-group">
            <label className="setting-label" htmlFor="username">Username</label>
            <input
              id="username"
              className="setting-input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your name"
              autoFocus
              disabled={loading}
            />
          </div>

          <div className="setting-group">
            <span className="setting-label">I am a...</span>
            <div className="role-picker">
              <button
                type="button"
                className={`role-option ${role === "biker" ? "role-option--active" : ""}`}
                onClick={() => setRole("biker")}
                disabled={loading}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="18.5" cy="17.5" r="3.5" />
                  <circle cx="5.5" cy="17.5" r="3.5" />
                  <path d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h2" />
                </svg>
                <span className="role-option-label">Biker</span>
                <span className="role-option-desc">View my routes</span>
              </button>
              <button
                type="button"
                className={`role-option ${role === "planner" ? "role-option--active" : ""}`}
                onClick={() => setRole("planner")}
                disabled={loading}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
                <span className="role-option-label">Planner</span>
                <span className="role-option-desc">Manage all routes</span>
              </button>
            </div>
          </div>

          {error && (
            <div className="login-error">{error}</div>
          )}

          <button className="btn btn-primary login-btn" type="submit" disabled={loading}>
            {loading ? (
              <>
                <span className="upload-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                Signing in...
              </>
            ) : (
              "Sign In"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
