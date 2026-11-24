export type ChatLanguage = "auto" | "en" | "zh" | "ja";

export type MessageRole = "user" | "assistant";

export interface Conversation {
  id: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  language: string;
  emotion: string | null;
  expression: string | null;
  motion: string | null;
  created_at: string;
}

export type ServerEvent =
  | {
      type: "user_message_saved" | "assistant_message";
      message: ChatMessage;
    }
  | {
      type: "error";
      message: string;
    };