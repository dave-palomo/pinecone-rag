import { describe, expect, it, vi } from "vitest";

import {
  OpenAIEmbeddingProvider,
  OpenAILanguageModel,
  type OpenAIClientLike,
} from "../src/shared/openai-services";
import { OpenAIServiceError } from "../src/shared/errors";

function createClient(
  embeddingCreate: OpenAIClientLike["embeddings"]["create"],
  responseCreate: OpenAIClientLike["responses"]["create"] = async () => ({ output_text: "answer" }),
): OpenAIClientLike {
  return {
    embeddings: { create: embeddingCreate },
    responses: { create: responseCreate },
  };
}

describe("OpenAI adapters", () => {
  it("batches embeddings, restores provider indexes, and validates dimensions", async () => {
    const create = vi.fn(async (request: { input: string[] }) => ({
      data: request.input
        .map((text, index) => ({ index, embedding: [text.length, 1] }))
        .reverse(),
    }));
    const provider = new OpenAIEmbeddingProvider(
      "unused",
      "embedding-model",
      2,
      2,
      createClient(create),
    );

    await expect(provider.embedTexts(["a", "bb", "ccc"])).resolves.toEqual([
      [1, 1],
      [2, 1],
      [3, 1],
    ]);
    expect(create).toHaveBeenCalledTimes(2);
  });

  it("translates malformed embeddings and empty LLM answers", async () => {
    const badEmbeddings = new OpenAIEmbeddingProvider(
      "unused",
      "embedding-model",
      2,
      10,
      createClient(async () => ({ data: [{ index: 0, embedding: [1] }] })),
    );
    await expect(badEmbeddings.embedTexts(["text"])).rejects.toBeInstanceOf(OpenAIServiceError);

    const model = new OpenAILanguageModel(
      "unused",
      "llm-model",
      createClient(async () => ({ data: [] }), async () => ({ output_text: "   " })),
    );
    await expect(model.answer("prompt")).rejects.toBeInstanceOf(OpenAIServiceError);
  });

  it("uses the stateless Responses API request shape", async () => {
    const responseCreate = vi.fn(async () => ({ output_text: "  Grounded answer. " }));
    const model = new OpenAILanguageModel(
      "unused",
      "llm-model",
      createClient(async () => ({ data: [] }), responseCreate),
    );

    await expect(model.answer("contextual prompt")).resolves.toBe("Grounded answer.");
    expect(responseCreate).toHaveBeenCalledWith({
      model: "llm-model",
      input: "contextual prompt",
      store: false,
    });
  });
});
