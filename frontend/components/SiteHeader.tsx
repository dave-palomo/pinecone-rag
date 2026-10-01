"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MoonIcon, SunIcon } from "@/components/icons";
import styles from "./ui.module.css";

const navigation = [
  { href: "/docs", label: "Documents" },
  { href: "/ask", label: "Ask" },
] as const;

type Theme = "light" | "dark";

export function SiteHeader() {
  const pathname = usePathname();
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const current = document.documentElement.getAttribute("data-theme");
    if (current === "dark" || current === "light") {
      setTheme(current);
    }
  }, []);

  function toggleTheme() {
    const next: Theme = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {}
  }

  return (
    <header className={styles.siteHeader}>
      <div className={styles.headerInner}>
        <Link className={styles.brand} href="/" aria-label="Doc Q&A Portal home">
          Doc Q&amp;A Portal
        </Link>
        <nav className={styles.navigation} aria-label="Primary navigation">
          {navigation.map((item) => {
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                className={isActive ? styles.navLinkActive : styles.navLink}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <button
          className={styles.themeToggle}
          type="button"
          onClick={toggleTheme}
          aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
        >
          {theme === "light" ? (
            <MoonIcon className={styles.themeToggleIcon} />
          ) : (
            <SunIcon className={styles.themeToggleIcon} />
          )}
        </button>
      </div>
    </header>
  );
}
