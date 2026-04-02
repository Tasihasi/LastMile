import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTheme } from "../hooks/useTheme";

import plannerGuide from "../content/user-guide-planner.md?raw";
import bikerGuide from "../content/user-guide-biker.md?raw";

type DocTab = "planner" | "biker";

interface TocItem {
  id: string;
  text: string;
  level: number;
}

function buildToc(md: string): TocItem[] {
  const items: TocItem[] = [];
  for (const line of md.split("\n")) {
    const match = line.match(/^(#{2,3})\s+(.+)/);
    if (!match) continue;
    const level = match[1].length;
    const text = match[2]
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/[`*]/g, "");
    const id = text
      .toLowerCase()
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
    items.push({ id, text, level });
  }
  return items;
}

export function DocsPage() {
  const navigate = useNavigate();
  const { theme, toggle: toggleTheme } = useTheme();
  const [tab, setTab] = useState<DocTab>("planner");
  const [activeId, setActiveId] = useState<string>("");
  const [tocOpen, setTocOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const content = tab === "planner" ? plannerGuide : bikerGuide;
  const toc = buildToc(content);

  // Track which heading is in view + reset scroll on tab change
  useEffect(() => {
    const container = contentRef.current;
    if (!container) return;

    container.scrollTo(0, 0);

    const headings = container.querySelectorAll<HTMLElement>("h2[id], h3[id]");
    if (!headings.length) return;

    const onScroll = () => {
      let current = "";
      for (const h of headings) {
        if (h.offsetTop - container.scrollTop <= 80) {
          current = h.id;
        }
      }
      setActiveId(current);
    };

    container.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => container.removeEventListener("scroll", onScroll);
  }, [tab]);

  const scrollToId = useCallback(
    (id: string) => {
      const el = contentRef.current?.querySelector(`#${CSS.escape(id)}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        setActiveId(id);
      }
      setTocOpen(false);
    },
    []
  );

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-left">
          <button className="btn btn-ghost" onClick={() => navigate("/")}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Back
          </button>
        </div>
        <div className="app-header-right">
          <button
            className="docs-toc-toggle"
            onClick={() => setTocOpen(!tocOpen)}
            aria-label="Table of contents"
            title="Table of contents"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="8" y1="6" x2="21" y2="6" />
              <line x1="8" y1="12" x2="21" y2="12" />
              <line x1="8" y1="18" x2="21" y2="18" />
              <line x1="3" y1="6" x2="3.01" y2="6" />
              <line x1="3" y1="12" x2="3.01" y2="12" />
              <line x1="3" y1="18" x2="3.01" y2="18" />
            </svg>
          </button>
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          >
            {theme === "light" ? (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
            )}
          </button>
        </div>
      </header>

      <div className="docs-layout">
        {/* Sidebar */}
        {tocOpen && <div className="docs-sidebar-overlay" onClick={() => setTocOpen(false)} />}
        <aside className={`docs-sidebar ${tocOpen ? "docs-sidebar--open" : ""}`}>
          {/* Tab switcher */}
          <div className="docs-tab-switcher">
            <button
              className={`docs-tab ${tab === "planner" ? "docs-tab--active" : ""}`}
              onClick={() => setTab("planner")}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="3" y1="9" x2="21" y2="9" />
                <line x1="9" y1="21" x2="9" y2="9" />
              </svg>
              Planner Guide
            </button>
            <button
              className={`docs-tab ${tab === "biker" ? "docs-tab--active" : ""}`}
              onClick={() => setTab("biker")}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="18.5" cy="17.5" r="3.5" />
                <circle cx="5.5" cy="17.5" r="3.5" />
                <polyline points="15 4 18 4 20 8" />
                <path d="M5.5 17.5L9 8h5l3 9" />
              </svg>
              Biker Guide
            </button>
          </div>

          {/* Table of contents */}
          <nav className="docs-toc">
            <div className="docs-toc-title">Contents</div>
            <ul className="docs-toc-list">
              {toc.map((item) => (
                <li key={item.id}>
                  <button
                    className={`docs-toc-link ${item.level === 3 ? "docs-toc-link--sub" : ""} ${activeId === item.id ? "docs-toc-link--active" : ""}`}
                    onClick={() => scrollToId(item.id)}
                  >
                    {item.text}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        {/* Content */}
        <main className="docs-content" ref={contentRef}>
          <div className="docs-content-inner">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => (
                  <h1 className="docs-h1">{children}</h1>
                ),
                h2: ({ children, ...props }) => {
                  const id = String(children)
                    .toLowerCase()
                    .replace(/[^\w\s-]/g, "")
                    .replace(/\s+/g, "-")
                    .replace(/-+/g, "-")
                    .replace(/^-|-$/g, "");
                  return <h2 id={id} className="docs-h2" {...props}>{children}</h2>;
                },
                h3: ({ children, ...props }) => {
                  const id = String(children)
                    .toLowerCase()
                    .replace(/[^\w\s-]/g, "")
                    .replace(/\s+/g, "-")
                    .replace(/-+/g, "-")
                    .replace(/^-|-$/g, "");
                  return <h3 id={id} className="docs-h3" {...props}>{children}</h3>;
                },
                table: ({ children }) => (
                  <div className="docs-table-wrap">
                    <table className="docs-table">{children}</table>
                  </div>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="docs-note">{children}</blockquote>
                ),
                code: ({ children, className }) => {
                  if (className) {
                    return (
                      <pre className="docs-codeblock">
                        <code>{children}</code>
                      </pre>
                    );
                  }
                  return <code className="docs-inline-code">{children}</code>;
                },
                pre: ({ children }) => <>{children}</>,
                hr: () => <hr className="docs-hr" />,
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </main>
      </div>
    </div>
  );
}
