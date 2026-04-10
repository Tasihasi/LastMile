import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthContext, useAuthProvider } from "./hooks/useAuth";
import { SharedRouteView } from "./components/SharedRouteView";
import { DocsPage } from "./components/DocsPage";
import "./index.css";
import App from "./App.tsx";

// eslint-disable-next-line react-refresh/only-export-components
function Root() {
  const auth = useAuthProvider();

  if (auth.loading) {
    return (
      <div className="app" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span className="upload-spinner" />
      </div>
    );
  }

  return (
    <AuthContext.Provider value={auth}>
      <BrowserRouter>
        <Routes>
          <Route path="/shared/:shareId" element={<SharedRouteView />} />
          <Route path="/docs" element={<DocsPage />} />
          {/* Remount App on login/logout so no state leaks between users. */}
          <Route path="*" element={<App key={auth.user?.id ?? "anon"} />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>
);
