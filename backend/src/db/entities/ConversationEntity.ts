import { EntitySchema } from "typeorm";

export interface ConversationEntity {
  id: string;
  userId: string;
  title: string | null;
  createdAt: Date;
}

export const ConversationEntitySchema = new EntitySchema<ConversationEntity>({
  name: "Conversation",
  tableName: "conversations",
  columns: {
    id: { type: "uuid", primary: true, generated: "uuid" },
    userId: { name: "user_id", type: "varchar", length: 64 },
    title: { type: "text", nullable: true },
    createdAt: { name: "created_at", type: "timestamptz", default: "NOW()" },
  },
});
