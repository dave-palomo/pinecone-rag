import { getEncoding } from "js-tiktoken";

import type { Chunk, ChunkingService } from "./domain";

export interface TokenCodec {
  encode(text: string): Iterable<number>;
  decode(tokens: number[]): string;
}

function createDefaultCodec(): TokenCodec {
  const encoding = getEncoding("cl100k_base");
  return {
    encode: (text) => encoding.encode(text),
    decode: (tokens) => encoding.decode(tokens),
  };
}

export class TokenChunker implements ChunkingService {
  private readonly codec: TokenCodec;

  constructor(
    private readonly chunkSize = 600,
    private readonly chunkOverlap = 100,
    codec?: TokenCodec,
  ) {
    if (!Number.isInteger(chunkSize) || chunkSize <= 0) {
      throw new Error("chunkSize must be a positive integer");
    }
    if (!Number.isInteger(chunkOverlap) || chunkOverlap < 0) {
      throw new Error("chunkOverlap must be a non-negative integer");
    }
    if (chunkOverlap >= chunkSize) {
      throw new Error("chunkOverlap must be smaller than chunkSize");
    }
    this.codec = codec ?? createDefaultCodec();
  }

  split(text: string): Chunk[] {
    const tokens = [...this.codec.encode(text)];
    if (tokens.length === 0) return [];

    const step = this.chunkSize - this.chunkOverlap;
    const chunks: Chunk[] = [];

    for (let start = 0; start < tokens.length; start += step) {
      const chunkTokens = tokens.slice(start, start + this.chunkSize);
      if (chunkTokens.length === 0) break;
      chunks.push({
        index: chunks.length,
        text: this.codec.decode(chunkTokens),
        tokenCount: chunkTokens.length,
      });
      if (start + this.chunkSize >= tokens.length) break;
    }

    return chunks;
  }
}

export function buildVectorId(docId: string, chunkIndex: number): string {
  if (!Number.isInteger(chunkIndex) || chunkIndex < 0) {
    throw new Error("chunkIndex must be a non-negative integer");
  }
  return `${docId}#chunk-${chunkIndex}`;
}
