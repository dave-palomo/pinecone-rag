import type { Metadata } from "next";
import { PageIntro } from "@/components/PageIntro";
import { QuestionForm } from "@/components/QuestionForm";
import styles from "@/components/ui.module.css";

export const metadata: Metadata = {
  title: "Ask",
};

export default function AskPage() {
  return (
    <main id="main-content" className={styles.pageShell}>
      <PageIntro
        title="Ask your documents"
        description="Get an answer grounded in the content you have ingested."
      />
      <QuestionForm />
    </main>
  );
}
