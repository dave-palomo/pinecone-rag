import type { EmbeddingProvider, LanguageModel, VectorStore } from "./domain";
import { OpenAIServiceError } from "./errors";
import { buildRagPrompt, buildSources } from "./prompting";
import type { AskResponse } from "./schemas";

export const NoMatchAnswer = "I couldn't find relevant information in the provided documents.";

export class RagService {
  constructor(
    private readonly embedder: EmbeddingProvider,
    private readonly vectorStore: VectorStore,
    private readonly languageModel: LanguageModel,
    private readonly topK: number,
  ) {
    if (!Number.isInteger(topK) || topK <= 0) {
      throw new Error("topK must be a positive integer");
    }
  }

  async ask(question: string): Promise<AskResponse> {
    const embeddings = await this.embedder.embedTexts([question]);
    if (embeddings.length !== 1 || !embeddings[0]) {
      throw new OpenAIServiceError("The question embedding response was invalid.");
    }

    const chunks = await this.vectorStore.query(embeddings[0], this.topK);
    if (chunks.length === 0) {
      return { answer: NoMatchAnswer, sources: [] };
    }

    const answer = await this.languageModel.answer(buildRagPrompt(question, chunks));
    return { answer, sources: buildSources(chunks) };
  }
}
