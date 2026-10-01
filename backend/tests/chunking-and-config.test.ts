import { describe, expect, it } from "vitest";

import { buildVectorId, TokenChunker, type TokenCodec } from "../src/shared/chunking";
import { getSettings, validateProviderConfiguration } from "../src/shared/config";
import { ConfigurationError } from "../src/shared/errors";

const characterCodec: TokenCodec = {
  encode: (text) => [...text].map((character) => character.codePointAt(0) ?? 0),
  decode: (tokens) => String.fromCodePoint(...tokens),
};

describe("TokenChunker", () => {
  it("preserves order, overlap, final partial chunk, and zero-based indexes", () => {
    const chunker = new TokenChunker(4, 1, characterCodec);

    expect(chunker.split("abcdefghi")).toEqual([
      { index: 0, text: "abcd", tokenCount: 4 },
      { index: 1, text: "defg", tokenCount: 4 },
      { index: 2, text: "ghi", tokenCount: 3 },
    ]);
  });

  it("rejects invalid overlap and builds deterministic IDs", () => {
    expect(() => new TokenChunker(4, 4, characterCodec)).toThrow("chunkOverlap");
    expect(() => buildVectorId("refund-policy", -1)).toThrow("chunkIndex");
    expect(buildVectorId("refund-policy", 2)).toBe("refund-policy#chunk-2");
  });
});

describe("configuration", () => {
  it("validates numeric and relational settings", () => {
    expect(() => getSettings({ CHUNK_SIZE: "100", CHUNK_OVERLAP: "100" })).toThrow(
      ConfigurationError,
    );
    expect(() => getSettings({ ASK_TOP_K: "0" })).toThrow(ConfigurationError);
  });

  it("requires only the providers needed by each route", () => {
    const ingestSettings = getSettings({
      OPENAI_API_KEY: "test",
      PINECONE_API_KEY: "test",
      PINECONE_INDEX: "test-index",
    });
    expect(() => validateProviderConfiguration(ingestSettings, false)).not.toThrow();
    expect(() => validateProviderConfiguration(ingestSettings, true)).toThrow(ConfigurationError);
  });
});
