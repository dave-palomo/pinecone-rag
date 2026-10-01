export type DocumentInput = {
  id: string;
  title: string;
  content: string;
};

export type IngestRequest = {
  documents: DocumentInput[];
};

export type IngestResponse = {
  ingestedDocuments: number;
  ingestedChunks: number;
};

export type AskRequest = {
  question: string;
};

export type Source = {
  docId: string;
  title: string;
};

export type AskResponse = {
  answer: string;
  sources: Source[];
};

export type ApiErrorResponse = {
  error: {
    code: string;
    message: string;
  };
};
