import { buildVectorId } from "./chunking";
import type { ChunkingService, EmbeddingProvider, VectorRecord, VectorStore } from "./domain";
import { InvalidRequestError, OpenAIServiceError } from "./errors";
import type { DocumentInput, IngestResponse } from "./schemas";

export class IngestionService {
  constructor(
    private readonly chunker: ChunkingService,
    private readonly embedder: EmbeddingProvider,
    private readonly vectorStore: VectorStore,
  ) {}

  async ingest(documents: readonly DocumentInput[]): Promise<IngestResponse> {
    let ingestedDocuments = 0;
    let ingestedChunks = 0;

    for (const document of documents) {
      const chunks = this.chunker.split(document.content);
      if (chunks.length === 0) {
        throw new InvalidRequestError("Tokenization produced no document chunks.");
      }

      const embeddings = await this.embedder.embedTexts(chunks.map((chunk) => chunk.text));
      if (embeddings.length !== chunks.length) {
        throw new OpenAIServiceError(
          "The embedding count does not match the document chunk count.",
        );
      }

      const records: VectorRecord[] = chunks.map((chunk, index) => {
        const values = embeddings[index];
        if (!values) {
          throw new OpenAIServiceError("The embedding provider returned an incomplete result.");
        }

        return {
          id: buildVectorId(document.id, chunk.index),
          values,
          metadata: {
            docId: document.id,
            title: document.title,
            chunkText: chunk.text,
            chunkIndex: chunk.index,
          },
        };
      });

      // New vectors are completely embedded and validated before replacement begins.
      const oldIds = await this.vectorStore.listDocumentVectorIds(document.id);
      await this.vectorStore.deleteIds(oldIds);
      await this.vectorStore.upsert(records);

      ingestedDocuments += 1;
      ingestedChunks += records.length;
    }

    return { ingestedDocuments, ingestedChunks };
  }
}
