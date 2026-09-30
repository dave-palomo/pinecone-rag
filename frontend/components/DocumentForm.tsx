import type { DocumentInput } from "@/lib/types";
import styles from "./ui.module.css";

export type DocumentFieldErrors = Partial<Record<keyof DocumentInput, string>>;

type DocumentFormProps = {
  document: DocumentInput;
  errors?: DocumentFieldErrors;
  index: number;
  onChange: (field: keyof DocumentInput, value: string) => void;
  onRemove?: () => void;
};

export function DocumentForm({
  document,
  errors,
  index,
  onChange,
  onRemove,
}: DocumentFormProps) {
  const documentNumber = index + 1;
  const idPrefix = `document-${documentNumber}`;

  return (
    <fieldset className={styles.documentForm}>
      <legend className={styles.documentLegend}>
        <span>Document {documentNumber}</span>
        {onRemove ? (
          <button className={styles.removeButton} type="button" onClick={onRemove}>
            Remove
          </button>
        ) : null}
      </legend>

      <div className={styles.field}>
        <label htmlFor={`${idPrefix}-id`}>Document ID</label>
        <input
          id={`${idPrefix}-id`}
          name={`${idPrefix}-id`}
          value={document.id}
          onChange={(event) => onChange("id", event.target.value)}
          placeholder="refund-policy"
          autoComplete="off"
          aria-invalid={Boolean(errors?.id)}
          aria-describedby={errors?.id ? `${idPrefix}-id-error` : undefined}
        />
        {errors?.id ? (
          <p id={`${idPrefix}-id-error`} className={styles.fieldError}>
            {errors.id}
          </p>
        ) : null}
      </div>

      <div className={styles.field}>
        <label htmlFor={`${idPrefix}-title`}>Title</label>
        <input
          id={`${idPrefix}-title`}
          name={`${idPrefix}-title`}
          value={document.title}
          onChange={(event) => onChange("title", event.target.value)}
          placeholder="Refund Policy"
          autoComplete="off"
          aria-invalid={Boolean(errors?.title)}
          aria-describedby={errors?.title ? `${idPrefix}-title-error` : undefined}
        />
        {errors?.title ? (
          <p id={`${idPrefix}-title-error`} className={styles.fieldError}>
            {errors.title}
          </p>
        ) : null}
      </div>

      <div className={styles.field}>
        <label htmlFor={`${idPrefix}-content`}>Content</label>
        <textarea
          id={`${idPrefix}-content`}
          name={`${idPrefix}-content`}
          value={document.content}
          onChange={(event) => onChange("content", event.target.value)}
          placeholder="Enter the full document text..."
          rows={6}
          aria-invalid={Boolean(errors?.content)}
          aria-describedby={
            errors?.content ? `${idPrefix}-content-error` : undefined
          }
        />
        {errors?.content ? (
          <p id={`${idPrefix}-content-error`} className={styles.fieldError}>
            {errors.content}
          </p>
        ) : null}
      </div>
    </fieldset>
  );
}
