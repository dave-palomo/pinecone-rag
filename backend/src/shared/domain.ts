export interface Chunk {
  index: number;
  text: string;
  tokenCount: number;
}

export type VectorMetadata = {
  docId: string;
  title: string;
  chunkText: string;
  chunkIndex: number;
  [key: string]: string | number | boolean | string[];
};

export interface VectorRecord {
  id: string;
  values: number[];
  metadata: VectorMetadata;
}

export interface RetrievedChunk {
  id: string;
  score: number;
  docId: string;
  title: string;
  chunkText: string;
  chunkIndex: number;
}

export interface ChunkingService {
  split(text: string): Chunk[];
}

export interface EmbeddingProvider {
  embedTexts(texts: readonly string[]): Promise<number[][]>;
}

export interface LanguageModel {
  answer(prompt: string): Promise<string>;
}

export interface VectorStore {
  listDocumentVectorIds(docId: string): Promise<string[]>;
  deleteIds(ids: readonly string[]): Promise<void>;
  upsert(records: readonly VectorRecord[]): Promise<void>;
  query(vector: readonly number[], topK: number): Promise<RetrievedChunk[]>;
}
