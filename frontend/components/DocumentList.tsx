"use client";

import { FormEvent, useState } from "react";
import { ingestDocuments } from "@/lib/api";
import type { DocumentInput, IngestResponse } from "@/lib/types";
import {
  DocumentForm,
  type DocumentFieldErrors,
} from "@/components/DocumentForm";
import { PlusIcon } from "@/components/icons";
import { StatusMessage } from "@/components/StatusMessage";
import styles from "./ui.module.css";

type DocumentDraft = DocumentInput & { key: string };

const EMPTY_DOCUMENT: DocumentDraft = {
  key: "document-1",
  id: "",
  title: "",
  content: "",
};

function validateDocuments(documents: DocumentDraft[]): DocumentFieldErrors[] {
  const errors = documents.map<DocumentFieldErrors>((document) => ({
    id: document.id.trim() ? undefined : "Enter a document ID.",
    title: document.title.trim() ? undefined : "Enter a document title.",
    content: document.content.trim() ? undefined : "Enter document content.",
  }));

  const idCounts = new Map<string, number>();
  for (const document of documents) {
    const id = document.id.trim();
    if (id) {
      idCounts.set(id, (idCounts.get(id) ?? 0) + 1);
    }
  }

  documents.forEach((document, index) => {
    const id = document.id.trim();
    if (id && (idCounts.get(id) ?? 0) > 1) {
      errors[index].id = "Document IDs must be unique in this request.";
    }
  });

  return errors;
}

function hasValidationErrors(errors: DocumentFieldErrors[]): boolean {
  return errors.some((documentErrors) =>
    Object.values(documentErrors).some(Boolean),
  );
}

export function DocumentList() {
  const [documents, setDocuments] = useState<DocumentDraft[]>([EMPTY_DOCUMENT]);
  const [fieldErrors, setFieldErrors] = useState<DocumentFieldErrors[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function addDocument() {
    setDocuments((current) => [
      ...current,
      { key: crypto.randomUUID(), id: "", title: "", content: "" },
    ]);
    setFieldErrors([]);
    setResult(null);
    setError(null);
  }

  function removeDocument(key: string) {
    setDocuments((current) => current.filter((document) => document.key !== key));
    setFieldErrors([]);
    setResult(null);
    setError(null);
  }

  function updateDocument(
    key: string,
    field: keyof DocumentInput,
    value: string,
  ) {
    setDocuments((current) =>
      current.map((document) =>
        document.key === key ? { ...document, [field]: value } : document,
      ),
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    const validationErrors = validateDocuments(documents);
    setFieldErrors(validationErrors);
    setResult(null);
    setError(null);

    if (hasValidationErrors(validationErrors)) {
      setError("Review the highlighted fields before submitting.");
      return;
    }

    const payload = documents.map(({ id, title, content }) => ({
      id: id.trim(),
      title: title.trim(),
      content: content.trim(),
    }));

    setIsSubmitting(true);

    try {
      const response = await ingestDocuments(payload);
      setResult(response);
      setDocuments([{ ...EMPTY_DOCUMENT }]);
      setFieldErrors([]);
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
    <form className={styles.documentList} onSubmit={handleSubmit} noValidate>
      <div className={styles.statusStack}>
        {result ? (
          <StatusMessage
            type="success"
            title="Success"
            message={`${result.ingestedDocuments} ${result.ingestedDocuments === 1 ? "document" : "documents"} ingested. ${result.ingestedChunks} ${result.ingestedChunks === 1 ? "chunk" : "chunks"} stored.`}
          />
        ) : null}
        {error ? <StatusMessage type="error" message={error} /> : null}
        {isSubmitting ? (
          <StatusMessage
            type="info"
            message="Ingesting documents..."
          />
        ) : null}
      </div>

      <div className={styles.documentStack}>
        {documents.map((document, index) => (
          <DocumentForm
            key={document.key}
            document={document}
            errors={fieldErrors[index]}
            index={index}
            onChange={(field, value) =>
              updateDocument(document.key, field, value)
            }
            onRemove={
              index > 0 ? () => removeDocument(document.key) : undefined
            }
          />
        ))}
      </div>

      <div className={styles.formActions}>
        <div>
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={addDocument}
            disabled={isSubmitting}
          >
            <PlusIcon className={styles.buttonIcon} />
            Add another document
          </button>
          <p className={styles.formHint}>At least one document is required.</p>
        </div>
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Ingesting..." : "Ingest documents"}
        </button>
      </div>
    </form>
  );
}
