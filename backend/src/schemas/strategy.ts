import { z } from "zod";

function isDateTimeString(value: string): boolean {
  return !Number.isNaN(Date.parse(value));
}

const FlexibleDateTimeString = z.string().refine(isDateTimeString, {
  message: "Invalid datetime",
});

export const CatalystCategorySchema = z.enum([
  "earnings",
  "product",
  "regulatory",
  "macro",
  "guidance",
  "other",
]);
export const CatalystImportanceSchema = z.enum(["high", "medium", "low"]);

export const StrategyCatalystSchema = z.object({
  description: z.string().max(300),
  // Window range (preferred). `expiresAt` kept as a legacy alias for windowEnd.
  windowStart: FlexibleDateTimeString.nullable().optional(),
  windowEnd: FlexibleDateTimeString.nullable().optional(),
  category: CatalystCategorySchema.optional().default("other"),
  importance: CatalystImportanceSchema.optional().default("medium"),
  expiresAt: FlexibleDateTimeString.nullable(),
  triggered: z.boolean(),
});
export type CatalystCategory = z.infer<typeof CatalystCategorySchema>;
export type CatalystImportance = z.infer<typeof CatalystImportanceSchema>;

export const StrategyMetadataSchema = z.object({
  source: z.enum([
    "bootstrap",
    "full_report",
    "deep_dive",
    "new_ideas",
    "manual_exploration",
    "migration",
  ]),
  status: z.enum(["provisional", "validated"]),
  generatedAt: FlexibleDateTimeString.nullable(),
  userGuidanceApplied: z.boolean().optional().default(false),
});

export const StrategyAssetScopeSchema = z.enum(["portfolio", "tracking"]);
export const StrategyTrackingStatusSchema = z.enum(["active", "muted", "archived"]);
export const StrategyStanceSchema = z.enum(["candidate", "watch", "pass", "avoid"]);
export const StrategyUrgencyLabelSchema = z.enum(["low", "medium", "high", "extra_high"]);

export const EvidenceSummarySchema = z.object({
  supporting: z.array(z.string()).default([]),
  conflicting: z.array(z.string()).default([]),
  uncertainties: z.array(z.string()).default([]),
});

export const StrategySchema = z.object({
  ticker: z.string().regex(/^[A-Z0-9.]{1,12}$/),
  updatedAt: FlexibleDateTimeString,
  version: z.number().int().min(1),
  verdict: z.enum(["BUY", "ADD", "HOLD", "REDUCE", "SELL", "CLOSE"]),
  confidence: z.enum(["high", "medium", "low"]),
  reasoning: z.string().max(800),
  timeframe: z.enum(["week", "months", "years", "long_term", "undefined"]),
  positionSizeILS: z.number(),
  positionWeightPct: z.number(),
  // Optimal-structure fields ────────────────────────────────────────────────
  thesis: z.string().max(400).nullable().optional(),
  keyRisks: z.array(z.string().max(200)).max(8).optional().default([]),
  evidenceSummary: EvidenceSummarySchema.optional(),
  nextEarningsDate: z.string().nullable().optional(),
  lastFullReportAt: FlexibleDateTimeString.nullable().optional(),
  lastQuickCheckAt: FlexibleDateTimeString.nullable().optional(),
  lastDailyBriefAt: FlexibleDateTimeString.nullable().optional(),
  // ─────────────────────────────────────────────────────────────────────────
  entryConditions: z
    .array(z.string().max(200))
    .max(5)
    .optional(),
  exitConditions: z
    .array(z.string().max(200))
    .max(5)
    .optional(),
  catalysts: z
    .array(StrategyCatalystSchema)
    .max(10)
    .optional()
    .default([]),
  bullCase: z.string().max(600).nullable(),
  bearCase: z.string().max(600).nullable(),
  lastDeepDiveAt: FlexibleDateTimeString.nullable(),
  deepDiveTriggeredBy: z.string().nullable(),
  metadata: StrategyMetadataSchema.optional(),
  assetScope: StrategyAssetScopeSchema.optional(),
  trackingStatus: StrategyTrackingStatusSchema.optional(),
  stance: StrategyStanceSchema.nullable().optional(),
  potentialScore: z.number().min(0).max(100).nullable().optional(),
  urgencyScore: z.number().min(0).max(100).nullable().optional(),
  urgencyLabel: StrategyUrgencyLabelSchema.nullable().optional(),
  portfolioFitScore: z.number().min(0).max(100).nullable().optional(),
  suggestedAllocationPct: z.number().min(0).max(100).nullable().optional(),
  suggestedAllocationILS: z.number().min(0).nullable().optional(),
  actionCatalysts: z
    .array(StrategyCatalystSchema)
    .max(10)
    .optional()
    .default([]),
  avoidConditions: z
    .array(z.string().max(200))
    .max(8)
    .optional()
    .default([]),
  nextReviewAt: FlexibleDateTimeString.nullable().optional(),
});

export type Strategy = z.infer<typeof StrategySchema>;
export type StrategyMetadata = z.infer<typeof StrategyMetadataSchema>;
export type StrategyAssetScope = z.infer<typeof StrategyAssetScopeSchema>;
export type StrategyTrackingStatus = z.infer<typeof StrategyTrackingStatusSchema>;
export type StrategyStance = z.infer<typeof StrategyStanceSchema>;
export type StrategyUrgencyLabel = z.infer<typeof StrategyUrgencyLabelSchema>;
