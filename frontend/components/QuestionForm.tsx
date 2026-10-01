"use client";

import { FormEvent, useState } from "react";
import { askQuestion } from "@/lib/api";
import type { AskResponse } from "@/lib/types";
import { AnswerResult } from "@/components/AnswerResult";
import { StatusMessage } from "@/components/StatusMessage";
import styles from "./ui.module.css";

export function QuestionForm() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    const trimmedQuestion = question.trim();
    setError(null);

    if (!trimmedQuestion) {
      setError("Enter a question before submitting.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await askQuestion(trimmedQuestion);
      setResult(response);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Something went wrong while contacting the backend.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <form className={styles.questionForm} onSubmit={handleSubmit} noValidate>
        <div className={styles.field}>
          <label htmlFor="question">Question</label>
          <textarea
            id="question"
            name="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="How long does standard domestic shipping normally take?"
            rows={6}
            aria-invalid={Boolean(error && !question.trim())}
          />
        </div>
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Asking..." : "Ask question"}
        </button>
      </form>

      <div className={styles.askStatus}>
        {error ? <StatusMessage type="error" message={error} /> : null}
        {isSubmitting ? (
          <StatusMessage
            type="info"
            message="Searching documents and generating answer..."
          />
        ) : null}
      </div>

      {result ? <AnswerResult result={result} /> : null}
    </div>
  );
}
