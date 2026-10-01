import type { Metadata } from "next";
import { DocumentList } from "@/components/DocumentList";
import { PageIntro } from "@/components/PageIntro";
import styles from "@/components/ui.module.css";

export const metadata: Metadata = {
  title: "Documents",
};

export default function DocumentsPage() {
  return (
    <main id="main-content" className={styles.pageShell}>
      <PageIntro
        title="Ingest documents"
        description="Add plain-text content to make it available for questions."
      />
      <DocumentList />
    </main>
  );
}
