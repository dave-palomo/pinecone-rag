import Link from "next/link";
import { TechStack } from "@/components/TechStack";
import styles from "./home.module.css";

export default function Home() {
  return (
    <main id="main-content" className={styles.main}>
      <section className={styles.hero} aria-labelledby="home-title">
        <div className={styles.titleBlock}>
          <h1 id="home-title">Bring your documents. Ask what matters.</h1>
          <p>
            A focused workspace for adding plain-text knowledge and getting
            answers grounded in the content you provide.
          </p>
        </div>

        <div className={styles.actions} aria-label="Get started">
          <Link className={styles.primaryAction} href="/docs">
            Add documents
            <span aria-hidden="true">→</span>
          </Link>
          <Link className={styles.secondaryAction} href="/ask">
            Ask a question
            <span aria-hidden="true">→</span>
          </Link>
        </div>

        <div className={styles.workflow} aria-label="Application workflow">
          <p>
            <span>01</span>
            Add one or more documents
          </p>
          <p>
            <span>02</span>
            Ask a natural-language question
          </p>
          <p>
            <span>03</span>
            Review the answer and its sources
          </p>
        </div>

        <TechStack />
      </section>
    </main>
  );
}
