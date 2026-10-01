import OpenAI from "openai";

import { TokenChunker } from "./chunking";
import { getSettings, validateProviderConfiguration } from "./config";
import { IngestionService } from "./ingestion";
import { OpenAIEmbeddingProvider, OpenAILanguageModel } from "./openai-services";
import { PineconeVectorStore } from "./pinecone-store";
import { RagService } from "./rag";

let openAIClient: OpenAI | undefined;
let vectorStorePromise: Promise<PineconeVectorStore> | undefined;
let ingestionServicePromise: Promise<IngestionService> | undefined;
let ragServicePromise: Promise<RagService> | undefined;

function getOpenAIClient(apiKey: string): OpenAI {
  openAIClient ??= new OpenAI({ apiKey });
  return openAIClient;
}

function getVectorStore(): Promise<PineconeVectorStore> {
  const settings = getSettings();
  vectorStorePromise ??= PineconeVectorStore.connect({
    apiKey: settings.pineconeApiKey,
    indexName: settings.pineconeIndex,
    namespace: settings.pineconeNamespace,
    dimensions: settings.embeddingDimensions,
  });
  return vectorStorePromise;
}

export async function getIngestionService(): Promise<IngestionService> {
  const settings = getSettings();
  validateProviderConfiguration(settings, false);
  ingestionServicePromise ??= getVectorStore().then(
    (vectorStore) =>
      new IngestionService(
        new TokenChunker(settings.chunkSize, settings.chunkOverlap),
        new OpenAIEmbeddingProvider(
          settings.openAIApiKey,
          settings.openAIEmbeddingModel,
          settings.embeddingDimensions,
          settings.embeddingBatchSize,
          getOpenAIClient(settings.openAIApiKey),
        ),
        vectorStore,
      ),
  );
  return ingestionServicePromise;
}

export async function getRagService(): Promise<RagService> {
  const settings = getSettings();
  validateProviderConfiguration(settings, true);
  ragServicePromise ??= getVectorStore().then(
    (vectorStore) =>
      new RagService(
        new OpenAIEmbeddingProvider(
          settings.openAIApiKey,
          settings.openAIEmbeddingModel,
          settings.embeddingDimensions,
          settings.embeddingBatchSize,
          getOpenAIClient(settings.openAIApiKey),
        ),
        vectorStore,
        new OpenAILanguageModel(
          settings.openAIApiKey,
          settings.openAILlmModel,
          getOpenAIClient(settings.openAIApiKey),
        ),
        settings.askTopK,
      ),
  );
  return ragServicePromise;
}

export function resetDependenciesForTests(): void {
  openAIClient = undefined;
  vectorStorePromise = undefined;
  ingestionServicePromise = undefined;
  ragServicePromise = undefined;
}
