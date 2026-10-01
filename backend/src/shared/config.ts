import { ConfigurationError } from "./errors";

export interface Settings {
  appEnv: string;
  allowedOrigin: string;
  openAIApiKey: string;
  openAIEmbeddingModel: string;
  openAILlmModel: string;
  embeddingDimensions: number;
  pineconeApiKey: string;
  pineconeIndex: string;
  pineconeNamespace: string;
  chunkSize: number;
  chunkOverlap: number;
  embeddingBatchSize: number;
  askTopK: number;
}

type Environment = Record<string, string | undefined>;

function getString(environment: Environment, name: string, fallback = ""): string {
  return (environment[name] ?? fallback).trim();
}

function positiveInteger(environment: Environment, name: string, fallback: number): number {
  const raw = getString(environment, name, String(fallback));
  const value = Number(raw);
  if (!Number.isInteger(value) || value <= 0) {
    throw new ConfigurationError(`${name} must be a positive integer.`);
  }
  return value;
}

function nonNegativeInteger(
  environment: Environment,
  name: string,
  fallback: number,
): number {
  const raw = getString(environment, name, String(fallback));
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 0) {
    throw new ConfigurationError(`${name} must be a non-negative integer.`);
  }
  return value;
}

export function getSettings(environment: Environment = process.env): Settings {
  const chunkSize = positiveInteger(environment, "CHUNK_SIZE", 600);
  const chunkOverlap = nonNegativeInteger(environment, "CHUNK_OVERLAP", 100);
  if (chunkOverlap >= chunkSize) {
    throw new ConfigurationError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.");
  }

  return {
    appEnv: getString(environment, "APP_ENV", "development") || "development",
    allowedOrigin:
      getString(environment, "ALLOWED_ORIGIN", "http://localhost:3000") ||
      "http://localhost:3000",
    openAIApiKey: getString(environment, "OPENAI_API_KEY"),
    openAIEmbeddingModel:
      getString(environment, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small") ||
      "text-embedding-3-small",
    openAILlmModel: getString(environment, "OPENAI_LLM_MODEL"),
    embeddingDimensions: positiveInteger(environment, "EMBEDDING_DIMENSIONS", 1536),
    pineconeApiKey: getString(environment, "PINECONE_API_KEY"),
    pineconeIndex: getString(environment, "PINECONE_INDEX"),
    pineconeNamespace: getString(environment, "PINECONE_NAMESPACE"),
    chunkSize,
    chunkOverlap,
    embeddingBatchSize: positiveInteger(environment, "EMBEDDING_BATCH_SIZE", 100),
    askTopK: positiveInteger(environment, "ASK_TOP_K", 3),
  };
}

export function validateProviderConfiguration(
  settings: Settings,
  includeLlm: boolean,
): void {
  const missing: string[] = [];
  if (!settings.openAIApiKey) missing.push("OPENAI_API_KEY");
  if (!settings.pineconeApiKey) missing.push("PINECONE_API_KEY");
  if (!settings.pineconeIndex) missing.push("PINECONE_INDEX");
  if (includeLlm && !settings.openAILlmModel) missing.push("OPENAI_LLM_MODEL");
  if (missing.length > 0) {
    throw new ConfigurationError(`Missing required configuration: ${missing.join(", ")}.`);
  }
}

export function getAllowedOrigin(environment: Environment = process.env): string {
  return (
    getString(environment, "ALLOWED_ORIGIN", "http://localhost:3000") ||
    "http://localhost:3000"
  );
}
