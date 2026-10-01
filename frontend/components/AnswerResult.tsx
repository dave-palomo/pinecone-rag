import type { AskResponse } from "@/lib/types";
import { SourcesList } from "@/components/SourcesList";
import styles from "./ui.module.css";

type AnswerResultProps = {
  result: AskResponse;
};

export function AnswerResult({ result }: AnswerResultProps) {
  return (
    <div className={styles.answerResult}>
      <section className={styles.resultSection} aria-labelledby="answer-heading">
        <h2 id="answer-heading">Answer</h2>
        <p className={styles.answerText}>{result.answer}</p>
      </section>
      <SourcesList sources={result.sources} />
    </div>
  );
}
