import { describe, expect, it, vi } from "vitest";

import type { PineconeIndexClient } from "../src/shared/pinecone-store";
import { PineconeVectorStore } from "../src/shared/pinecone-store";
import { PineconeServiceError } from "../src/shared/errors";

function fakeIndex(overrides: Partial<PineconeIndexClient> = {}): PineconeIndexClient {
  return {
    listPaginated: async () => ({ vectors: [] }),
    deleteMany: async () => undefined,
    upsert: async () => undefined,
    query: async () => ({ matches: [] }),
    ...overrides,
  };
}

describe("PineconeVectorStore", () => {
  it("lists every prefix page before replacing an existing document", async () => {
    const listPaginated = vi
      .fn()
      .mockResolvedValueOnce({
        vectors: [{ id: "refund-policy#chunk-0" }, { id: "other#chunk-0" }],
        pagination: { next: "next-page" },
      })
      .mockResolvedValueOnce({ vectors: [{ id: "refund-policy#chunk-1" }] });
    const store = new PineconeVectorStore(fakeIndex({ listPaginated }));

    await expect(store.listDocumentVectorIds("refund-policy")).resolves.toEqual([
      "refund-policy#chunk-0",
      "refund-policy#chunk-1",
    ]);
    expect(listPaginated).toHaveBeenNthCalledWith(1, { prefix: "refund-policy#chunk-", paginationToken: undefined });
    expect(listPaginated).toHaveBeenNthCalledWith(2, {
      prefix: "refund-policy#chunk-",
      paginationToken: "next-page",
    });
  });

  it("does not delete an empty ID list and parses only usable matches", async () => {
    const deleteMany = vi.fn(async () => undefined);
    const store = new PineconeVectorStore(
      fakeIndex({
        deleteMany,
        query: async () => ({
          matches: [
            {
              id: "refund-policy#chunk-0",
              score: 0.9,
              metadata: {
                docId: "refund-policy",
                title: "Refund Policy",
                chunkText: "No refunds on digital goods.",
                chunkIndex: 0,
              },
            },
            { id: "broken", score: 0.4, metadata: {} },
          ],
        }),
      }),
    );

    await store.deleteIds([]);
    expect(deleteMany).not.toHaveBeenCalled();
    await expect(store.query([0.1, 0.2], 3)).resolves.toEqual([
      {
        id: "refund-policy#chunk-0",
        score: 0.9,
        docId: "refund-policy",
        title: "Refund Policy",
        chunkText: "No refunds on digital goods.",
        chunkIndex: 0,
      },
    ]);
  });

  it("translates Pinecone provider failures", async () => {
    const store = new PineconeVectorStore(
      fakeIndex({ listPaginated: async () => Promise.reject(new Error("provider failure")) }),
    );
    await expect(store.listDocumentVectorIds("doc")).rejects.toBeInstanceOf(PineconeServiceError);
  });
});
