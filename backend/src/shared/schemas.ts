import { z } from "zod";

const SafeDocumentId = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,479}$/;

export const DocumentInputSchema = z
  .object({
    id: z
      .string()
      .trim()
      .min(1)
      .max(480)
      .regex(
        SafeDocumentId,
        "id must start with an alphanumeric character and contain only letters, numbers, dots, underscores, colons, or hyphens",
      ),
    title: z.string().trim().min(1),
    content: z.string().trim().min(1),
  })
  .strict();

export const IngestRequestSchema = z
  .object({ documents: z.array(DocumentInputSchema).min(1) })
  .strict()
  .superRefine((value, context) => {
    const ids = new Set<string>();
    for (const [index, document] of value.documents.entries()) {
      if (ids.has(document.id)) {
        context.addIssue({
          code: "custom",
          path: ["documents", index, "id"],
          message: "document ids must be unique within one request",
        });
      }
      ids.add(document.id);
    }
  });

export const AskRequestSchema = z
  .object({ question: z.string().trim().min(1) })
  .strict();

export const IngestResponseSchema = z.object({
  ingestedDocuments: z.number().int().nonnegative(),
  ingestedChunks: z.number().int().nonnegative(),
});

export const SourceSchema = z.object({
  docId: z.string(),
  title: z.string(),
});

export const AskResponseSchema = z.object({
  answer: z.string(),
  sources: z.array(SourceSchema),
});

export type DocumentInput = z.infer<typeof DocumentInputSchema>;
export type IngestRequest = z.infer<typeof IngestRequestSchema>;
export type AskRequest = z.infer<typeof AskRequestSchema>;
export type IngestResponse = z.infer<typeof IngestResponseSchema>;
export type Source = z.infer<typeof SourceSchema>;
export type AskResponse = z.infer<typeof AskResponseSchema>;
