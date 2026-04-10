import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[ErrorBoundary] caught error:", error, info.componentStack);
  }

  reset = (): void => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    if (this.props.fallback) return this.props.fallback(error, this.reset);

    return (
      <div className="error-boundary" role="alert">
        <div className="error-boundary-card">
          <h1 className="error-boundary-title">Something went wrong</h1>
          <p className="error-boundary-message">
            {error.message || "An unexpected error occurred."}
          </p>
          <div className="error-boundary-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                this.reset();
                window.location.reload();
              }}
            >
              Reload page
            </button>
            <button type="button" className="btn btn-secondary" onClick={this.reset}>
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }
}
