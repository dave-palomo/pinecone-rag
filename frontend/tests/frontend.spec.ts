import { expect, test, type Page } from "@playwright/test";

async function fillFirstDocument(page: Page) {
  await page.getByLabel("Document ID").fill("refund-policy");
  await page.getByLabel("Title").fill("Refund Policy");
  await page
    .getByLabel("Content")
    .fill("Full refund within 30 days with receipt.");
}

async function mockJsonEndpoint(
  page: Page,
  url: string,
  status: number,
  body: unknown,
) {
  await page.route(url, async (route) => {
    const resourceType = route.request().resourceType();
    if (resourceType !== "fetch" && resourceType !== "xhr") {
      await route.continue();
      return;
    }

    const corsHeaders = {
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Origin": "http://127.0.0.1:3000",
    };

    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: corsHeaders });
      return;
    }

    await route.fulfill({
      status,
      contentType: "application/json",
      headers: corsHeaders,
      body: JSON.stringify(body),
    });
  });
}

test("a document form can be added and removed", async ({ page }) => {
  await page.goto("/docs");

  await page.getByRole("button", { name: "Add another document" }).click();
  await expect(page.getByText("Document 2", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Remove" })).toBeVisible();

  await page.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByText("Document 2", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Document 1", { exact: true })).toBeVisible();
});

test("empty documents are rejected locally", async ({ page }) => {
  await page.goto("/docs");
  await page.getByRole("button", { name: "Ingest documents" }).click();

  await expect(
    page.getByText("Review the highlighted fields before submitting."),
  ).toBeVisible();
  await expect(page.getByText("Enter a document ID.")).toBeVisible();
  await expect(page.getByText("Enter a document title.")).toBeVisible();
  await expect(page.getByText("Enter document content.")).toBeVisible();
});

test("ingest success renders backend counts", async ({ page }) => {
  await mockJsonEndpoint(page, "**/ingest", 200, {
    ingestedDocuments: 1,
    ingestedChunks: 3,
  });
  await page.goto("/docs");
  await fillFirstDocument(page);
  await page.getByRole("button", { name: "Ingest documents" }).click();

  await expect(page.getByText("Success", { exact: true })).toBeVisible();
  await expect(
    page.getByText("1 document ingested. 3 chunks stored."),
  ).toBeVisible();
  await expect(page.getByLabel("Document ID")).toHaveValue("");
  await expect(page.getByLabel("Title")).toHaveValue("");
  await expect(page.getByLabel("Content")).toHaveValue("");
  await expect(page.getByLabel("Document ID")).toHaveCount(1);
});

test("ingest error renders the backend public message", async ({ page }) => {
  await mockJsonEndpoint(page, "**/ingest", 422, {
    error: {
      code: "VALIDATION_ERROR",
      message: "Invalid request payload.",
    },
  });
  await page.goto("/docs");
  await fillFirstDocument(page);
  await page.getByRole("button", { name: "Ingest documents" }).click();

  await expect(page.getByText("Invalid request payload.")).toBeVisible();
  await expect(page.getByLabel("Title")).toHaveValue("Refund Policy");
});

test("ask success renders the answer and every source", async ({ page }) => {
  await mockJsonEndpoint(page, "**/ask", 200, {
    answer: "Standard domestic shipping takes three to five business days.",
    sources: [
      { docId: "shipping-policy", title: "Shipping Policy" },
      { docId: "delivery-faq", title: "Delivery FAQ" },
    ],
  });
  await page.goto("/ask");
  await page.getByLabel("Question").fill("How long does shipping take?");
  await page.getByRole("button", { name: "Ask question" }).click();

  await expect(page.getByRole("heading", { name: "Answer" })).toBeVisible();
  await expect(
    page.getByText("Standard domestic shipping takes three to five business days."),
  ).toBeVisible();
  await expect(page.getByText("Shipping Policy")).toBeVisible();
  await expect(page.getByText("ID: shipping-policy")).toBeVisible();
  await expect(page.getByText("Delivery FAQ")).toBeVisible();
});

test("empty sources render safely", async ({ page }) => {
  await mockJsonEndpoint(page, "**/ask", 200, {
    answer: "I couldn't find relevant information.",
    sources: [],
  });
  await page.goto("/ask");
  await page.getByLabel("Question").fill("Who is the CEO?");
  await page.getByRole("button", { name: "Ask question" }).click();

  await expect(page.getByText("No sources available.")).toBeVisible();
});

test("ask error renders the backend public message", async ({ page }) => {
  await mockJsonEndpoint(page, "**/ask", 502, {
    error: {
      code: "OPENAI_ERROR",
      message: "Failed to process the request with the AI provider.",
    },
  });
  await page.goto("/ask");
  await page.getByLabel("Question").fill("What is the refund policy?");
  await page.getByRole("button", { name: "Ask question" }).click();

  await expect(
    page.getByText("Failed to process the request with the AI provider."),
  ).toBeVisible();
  await expect(page.getByLabel("Question")).toHaveValue(
    "What is the refund policy?",
  );
});
