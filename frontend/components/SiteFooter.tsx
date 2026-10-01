import { GitHubIcon, LinkedInIcon } from "@/components/icons";
import styles from "./ui.module.css";

const socialLinks = [
  {
    href: "https://www.linkedin.com/in/david-palomo-73811936/",
    label: "LinkedIn profile",
    Icon: LinkedInIcon,
  },
  {
    href: "https://github.com/dave-palomo",
    label: "GitHub profile",
    Icon: GitHubIcon,
  },
] as const;

export function SiteFooter() {
  return (
    <footer className={styles.siteFooter}>
      <div className={styles.footerInner}>
        <p className={styles.footerCopy}>
          &copy; 2026 David Palomo. All rights reserved.
        </p>
        <div className={styles.socialLinks}>
          {socialLinks.map(({ href, label, Icon }) => (
            <a
              key={href}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={label}
              className={styles.socialLink}
            >
              <Icon className={styles.socialIcon} />
            </a>
          ))}
        </div>
      </div>
    </footer>
  );
}
