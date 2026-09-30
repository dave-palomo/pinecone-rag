"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./ui.module.css";

const navigation = [
  { href: "/docs", label: "Documents" },
  { href: "/ask", label: "Ask" },
] as const;

export function SiteHeader() {
  const pathname = usePathname();

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
      </div>
    </header>
  );
}
