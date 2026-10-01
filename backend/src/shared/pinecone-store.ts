import { Pinecone } from "@pinecone-database/pinecone";
import type { IndexModel } from "@pinecone-database/pinecone";

import type { RetrievedChunk, VectorMetadata, VectorRecord, VectorStore } from "./domain";
import { PineconeServiceError } from "./errors";

interface PineconeListPage {
  vectors?: readonly { id?: string }[];
  pagination?: { next?: string };
}

interface PineconeRawMatch {
  id?: string;
  score?: number;
  metadata?: unknown;
}

export interface PineconeIndexClient {
  listPaginated(options: {
    prefix: string;
    paginationToken?: string;
  }): Promise<PineconeListPage>;
  deleteMany(options: { ids: string[] }): Promise<void>;
  upsert(options: {
    records: Array<{ id: string; values: number[]; metadata: VectorMetadata }>;
  }): Promise<void>;
  query(options: {
    vector: number[];
    topK: number;
    includeMetadata: true;
  }): Promise<{ matches: readonly PineconeRawMatch[] }>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseRetrievedChunk(match: PineconeRawMatch): RetrievedChunk | undefined {
  const score = match.score;
  if (
    !match.id ||
    typeof match.id !== "string" ||
    typeof score !== "number" ||
    !Number.isFinite(score)
  ) {
    return undefined;
  }
  if (!isRecord(match.metadata)) return undefined;

  const { docId, title, chunkText, chunkIndex } = match.metadata;
  if (
    typeof docId !== "string" ||
    !docId ||
    typeof title !== "string" ||
    !title ||
    typeof chunkText !== "string" ||
    !chunkText ||
    !Number.isInteger(chunkIndex) ||
    typeof chunkIndex !== "number" ||
    chunkIndex < 0
  ) {
    return undefined;
  }

  return {
    id: match.id,
    score,
    docId,
    title,
    chunkText,
    chunkIndex,
  };
}

export function validatePineconeIndex(description: IndexModel, expectedDimensions: number): void {
  if (description.deployment.deploymentType !== "managed") {
    throw new PineconeServiceError(
      "The Pinecone index must be a managed serverless index for prefix listing.",
    );
  }

  const denseFields = Object.values(description.schema.fields).filter(
    (field) => "type" in field && field.type === "dense_vector",
  );
  if (denseFields.length !== 1) {
    throw new PineconeServiceError("The Pinecone index must have exactly one dense vector field.");
  }
  const denseField = denseFields[0];
  if (!denseField || denseField.dimension !== expectedDimensions) {
    throw new PineconeServiceError(
      "The Pinecone index dimension does not match EMBEDDING_DIMENSIONS.",
    );
  }
  if (denseField.metric !== "cosine") {
    throw new PineconeServiceError("The Pinecone index metric must be cosine.");
  }
}

export class PineconeVectorStore implements VectorStore {
  constructor(private readonly index: PineconeIndexClient) {}

  static async connect(options: {
    apiKey: string;
    indexName: string;
    namespace: string;
    dimensions: number;
  }): Promise<PineconeVectorStore> {
    try {
      const pinecone = new Pinecone({ apiKey: options.apiKey });
      const description = await pinecone.indexes.describe(options.indexName);
      validatePineconeIndex(description, options.dimensions);
      const index = pinecone.index<VectorMetadata>({
        name: options.indexName,
        namespace: options.namespace,
      });
      return new PineconeVectorStore(index);
    } catch (error) {
      if (error instanceof PineconeServiceError) throw error;
      throw new PineconeServiceError("Unable to inspect or connect to the Pinecone index.");
    }
  }

  async listDocumentVectorIds(docId: string): Promise<string[]> {
    const prefix = `${docId}#chunk-`;
    const ids: string[] = [];
    const seenTokens = new Set<string>();
    let paginationToken: string | undefined;

    try {
      do {
        const page = await this.index.listPaginated({ prefix, paginationToken });
        for (const vector of page.vectors ?? []) {
          if (typeof vector.id === "string" && vector.id.startsWith(prefix)) {
            ids.push(vector.id);
          }
        }
        paginationToken = page.pagination?.next;
        if (paginationToken && seenTokens.has(paginationToken)) {
          throw new PineconeServiceError("Pinecone returned a repeated pagination token.");
        }
        if (paginationToken) seenTokens.add(paginationToken);
      } while (paginationToken);
      return ids;
    } catch (error) {
      if (error instanceof PineconeServiceError) throw error;
      throw new PineconeServiceError("Unable to list existing document vectors.");
    }
  }

  async deleteIds(ids: readonly string[]): Promise<void> {
    if (ids.length === 0) return;
    try {
      await this.index.deleteMany({ ids: [...ids] });
    } catch {
      throw new PineconeServiceError("Unable to replace the existing document.");
    }
  }

  async upsert(records: readonly VectorRecord[]): Promise<void> {
    if (records.length === 0) return;
    try {
      await this.index.upsert({
        records: records.map((record) => ({
          id: record.id,
          values: [...record.values],
          metadata: record.metadata,
        })),
      });
    } catch {
      throw new PineconeServiceError("Unable to store document vectors.");
    }
  }

  async query(vector: readonly number[], topK: number): Promise<RetrievedChunk[]> {
    try {
      const response = await this.index.query({
        vector: [...vector],
        topK,
        includeMetadata: true,
      });
      return response.matches
        .map(parseRetrievedChunk)
        .filter((match): match is RetrievedChunk => match !== undefined);
    } catch {
      throw new PineconeServiceError("Unable to search document vectors.");
    }
  }
}
