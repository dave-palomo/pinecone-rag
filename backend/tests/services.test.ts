import { describe, expect, it, vi } from "vitest";

import type { ChunkingService, EmbeddingProvider, LanguageModel, VectorStore } from "../src/shared/domain";
import { IngestionService } from "../src/shared/ingestion";
import { RagService, NoMatchAnswer } from "../src/shared/rag";

describe("IngestionService", () => {
  it("embeds every chunk before listing, deleting, and upserting", async () => {
    const events: string[] = [];
    const chunker: ChunkingService = {
      split: () => [
        { index: 0, text: "first", tokenCount: 1 },
        { index: 1, text: "second", tokenCount: 1 },
      ],
    };
    const embedder: EmbeddingProvider = {
      embedTexts: async () => {
        events.push("embed");
        return [
          [0.1, 0.2],
          [0.3, 0.4],
        ];
      },
    };
    const vectorStore: VectorStore = {
      listDocumentVectorIds: async () => {
        events.push("list");
        return ["doc#chunk-0"];
      },
      deleteIds: async () => {
        events.push("delete");
      },
      upsert: async (records) => {
        events.push("upsert");
        expect(records).toHaveLength(2);
        expect(records[1]?.metadata.chunkIndex).toBe(1);
      },
      query: async () => [],
    };

    const service = new IngestionService(chunker, embedder, vectorStore);
    await expect(
      service.ingest([{ id: "doc", title: "Document", content: "content" }]),
    ).resolves.toEqual({ ingestedDocuments: 1, ingestedChunks: 2 });
    expect(events).toEqual(["embed", "list", "delete", "upsert"]);
  });
});

describe("RagService", () => {
  it("does not call the LLM when no usable match exists", async () => {
    const answer = vi.fn(async () => "should not run");
    const service = new RagService(
      { embedTexts: async () => [[0.1, 0.2]] },
      {
        listDocumentVectorIds: async () => [],
        deleteIds: async () => undefined,
        upsert: async () => undefined,
        query: async () => [],
      },
      { answer },
      3,
    );

    await expect(service.ask("question")).resolves.toEqual({ answer: NoMatchAnswer, sources: [] });
    expect(answer).not.toHaveBeenCalled();
  });

  it("preserves retrieval order and deduplicates sources", async () => {
    const vectorStore: VectorStore = {
      listDocumentVectorIds: async () => [],
      deleteIds: async () => undefined,
      upsert: async () => undefined,
      query: async () => [
        { id: "a#0", score: 0.9, docId: "a", title: "A", chunkText: "first", chunkIndex: 0 },
        { id: "a#1", score: 0.8, docId: "a", title: "A", chunkText: "second", chunkIndex: 1 },
        { id: "b#0", score: 0.7, docId: "b", title: "B", chunkText: "third", chunkIndex: 0 },
      ],
    };
    const model: LanguageModel = { answer: async (prompt) => (prompt.includes("first") ? "grounded" : "wrong") };
    const service = new RagService({ embedTexts: async () => [[1, 2]] }, vectorStore, model, 3);

    await expect(service.ask("question")).resolves.toEqual({
      answer: "grounded",
      sources: [
        { docId: "a", title: "A" },
        { docId: "b", title: "B" },
      ],
    });
  });
});
