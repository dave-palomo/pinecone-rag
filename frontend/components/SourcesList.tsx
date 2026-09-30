import type { Source } from "@/lib/types";
import styles from "./ui.module.css";

type SourcesListProps = {
  sources: Source[];
};

export function SourcesList({ sources }: SourcesListProps) {
  return (
    <section className={styles.resultSection} aria-labelledby="sources-heading">
      <h2 id="sources-heading">Sources</h2>
      {sources.length > 0 ? (
        <ul className={styles.sourcesList}>
          {sources.map((source, index) => (
            <li key={`${source.docId}-${index}`}>
              <strong>{source.title}</strong>
              <span>ID: {source.docId}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.emptySources}>No sources available.</p>
      )}
    </section>
  );
}
