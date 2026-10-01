import OpenAI from "openai";

import type { EmbeddingProvider, LanguageModel } from "./domain";
import { OpenAIServiceError } from "./errors";

export interface OpenAIClientLike {
  embeddings: {
    create(input: {
      model: string;
      input: string[];
      dimensions: number;
      encoding_format: "float";
    }): Promise<{ data: Array<{ index: number; embedding: number[] }> }>;
  };
  responses: {
    create(input: {
      model: string;
      input: string;
      store: false;
    }): Promise<{ output_text: string }>;
  };
}

function isFiniteVector(vector: unknown, dimensions: number): vector is number[] {
  return (
    Array.isArray(vector) &&
    vector.length === dimensions &&
    vector.every((value) => typeof value === "number" && Number.isFinite(value))
  );
}

export class OpenAIEmbeddingProvider implements EmbeddingProvider {
  private readonly client: OpenAIClientLike;

  constructor(
    apiKey: string,
    readonly model: string,
    readonly dimensions: number,
    readonly batchSize: number,
    client?: OpenAIClientLike,
  ) {
    if (!Number.isInteger(dimensions) || dimensions <= 0) {
      throw new Error("dimensions must be a positive integer");
    }
    if (!Number.isInteger(batchSize) || batchSize <= 0) {
      throw new Error("batchSize must be a positive integer");
    }
    this.client = client ?? new OpenAI({ apiKey });
  }

  async embedTexts(texts: readonly string[]): Promise<number[][]> {
    if (texts.length === 0) return [];

    const embeddings: number[][] = [];
    try {
      for (let offset = 0; offset < texts.length; offset += this.batchSize) {
        const batch = texts.slice(offset, offset + this.batchSize);
        const response = await this.client.embeddings.create({
          model: this.model,
          input: [...batch],
          dimensions: this.dimensions,
          encoding_format: "float",
        });
        const items = [...response.data].sort((left, right) => left.index - right.index);
        if (
          items.length !== batch.length ||
          items.some((item, index) => item.index !== index || !isFiniteVector(item.embedding, this.dimensions))
        ) {
          throw new OpenAIServiceError(
            "The embedding response did not match the request or configured dimensions.",
          );
        }
        embeddings.push(...items.map((item) => [...item.embedding]));
      }
    } catch (error) {
      if (error instanceof OpenAIServiceError) throw error;
      throw new OpenAIServiceError();
    }

    if (embeddings.length !== texts.length) {
      throw new OpenAIServiceError("The embedding response count did not match the request.");
    }
    return embeddings;
  }
}

export class OpenAILanguageModel implements LanguageModel {
  private readonly client: OpenAIClientLike;

  constructor(apiKey: string, readonly model: string, client?: OpenAIClientLike) {
    this.client = client ?? new OpenAI({ apiKey });
  }

  async answer(prompt: string): Promise<string> {
    try {
      const response = await this.client.responses.create({
        model: this.model,
        input: prompt,
        store: false,
      });
      const answer = response.output_text.trim();
      if (!answer) {
        throw new OpenAIServiceError("The AI service returned an empty answer.");
      }
      return answer;
    } catch (error) {
      if (error instanceof OpenAIServiceError) throw error;
      throw new OpenAIServiceError();
    }
  }
}
