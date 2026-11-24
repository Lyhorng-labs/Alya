import type { Conversation } from "./types";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export async function createConversation(): Promise<Conversation> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/conversations`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(
      `Failed to create conversation: ${response.status}`
    );
  }

  return response.json() as Promise<Conversation>;
}

export function getConversationSocketUrl(
  conversationId: string
): string {
  const url = new URL(API_BASE_URL);

  const protocol =
    url.protocol === "https:" ? "wss:" : "ws:";

  return (
    `${protocol}//${url.host}` +
    `/api/v1/ws/conversations/${conversationId}`
  );
}