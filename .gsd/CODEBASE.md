# Codebase Map

Generated: 2026-05-19T20:44:05Z | Files: 355 | Described: 0/355
<!-- gsd:codebase-meta {"generatedAt":"2026-05-19T20:44:05Z","fingerprint":"33b36a9fe5489fd833c8b5276da6e594802055f5","fileCount":355,"truncated":false} -->

### (root)/
- `.gitignore`
- `AGENTS.md`
- `deploy.sh`
- `README.md`

### backend/
- `backend/.env.example`
- `backend/package-lock.json`
- `backend/package.json`
- `backend/tsconfig.json`

### backend/scripts/
- `backend/scripts/migrateObservabilityToPostgres.mjs`
- `backend/scripts/run-tests.mjs`

### backend/src/
- `backend/src/app.ts`
- `backend/src/server.ts`

### backend/src/db/
- `backend/src/db/applicationDataSource.ts`

### backend/src/db/entities/
- *(30 files: 30 .ts)*

### backend/src/middleware/
- `backend/src/middleware/auth.ts`
- `backend/src/middleware/impersonation.ts`
- `backend/src/middleware/rateLimit.ts`
- `backend/src/middleware/userIsolation.ts`

### backend/src/routes/
- *(24 files: 24 .ts)*

### backend/src/schemas/
- `backend/src/schemas/analysts.ts`
- `backend/src/schemas/channels.ts`
- `backend/src/schemas/control.ts`
- `backend/src/schemas/index.ts`
- `backend/src/schemas/job.ts`
- `backend/src/schemas/notifications.ts`
- `backend/src/schemas/onboarding.ts`
- `backend/src/schemas/pilotFeature.ts`
- `backend/src/schemas/portfolio.ts`
- `backend/src/schemas/profile.ts`
- `backend/src/schemas/strategy.test.ts`
- `backend/src/schemas/strategy.ts`
- `backend/src/schemas/support.ts`

### backend/src/scripts/
- `backend/src/scripts/cleanupOpenClawWorkspaces.ts`
- `backend/src/scripts/migrateUserStateToPostgres.ts`
- `backend/src/scripts/migrateUserToStepQueue.ts`
- `backend/src/scripts/rebuildIndex.ts`
- `backend/src/scripts/replayOpeningLots.ts`
- `backend/src/scripts/supersedeStuckJob.test.ts`
- `backend/src/scripts/supersedeStuckJob.ts`
- `backend/src/scripts/verifyMigrationParity.ts`

### backend/src/services/
- *(87 files: 87 .ts)*

### backend/src/services/chat/
- `backend/src/services/chat/agentChat.ts`
- `backend/src/services/chat/chatSafetyPolicy.test.ts`
- `backend/src/services/chat/confirmationStore.ts`
- `backend/src/services/chat/conversationStore.savedChats.test.ts`
- `backend/src/services/chat/conversationStore.ts`
- `backend/src/services/chat/outputFilter.ts`
- `backend/src/services/chat/personaPrompt.ts`

### backend/src/services/chat/llmProviders/
- `backend/src/services/chat/llmProviders/anthropicProvider.ts`
- `backend/src/services/chat/llmProviders/geminiProvider.ts`
- `backend/src/services/chat/llmProviders/index.ts`
- `backend/src/services/chat/llmProviders/openAiProvider.ts`
- `backend/src/services/chat/llmProviders/openRouterProvider.ts`

### backend/src/services/chat/tools/
- `backend/src/services/chat/tools/actionTools.ts`
- `backend/src/services/chat/tools/readTools.ts`
- `backend/src/services/chat/tools/registry.ts`

### backend/src/services/dataSources/
- `backend/src/services/dataSources/cache.ts`
- `backend/src/services/dataSources/fundamentalsSource.ts`
- `backend/src/services/dataSources/macroSource.ts`
- `backend/src/services/dataSources/marketDataSource.ts`
- `backend/src/services/dataSources/sentimentSource.ts`

### backend/src/services/scheduler/
- `backend/src/services/scheduler/watchdog.ts`

### backend/src/services/security/
- `backend/src/services/security/adminAuditStore.ts`
- `backend/src/services/security/encryptedSecretsStore.ts`
- `backend/src/services/security/startupGuards.ts`

### backend/src/services/stepQueue/
- `backend/src/services/stepQueue/admission.ts`
- `backend/src/services/stepQueue/artifactIO.ts`
- `backend/src/services/stepQueue/completionEffects.ts`
- `backend/src/services/stepQueue/executor.ts`
- `backend/src/services/stepQueue/expansion.ts`
- `backend/src/services/stepQueue/featureFlag.ts`
- `backend/src/services/stepQueue/handlers.ts`
- `backend/src/services/stepQueue/handlerUtils.ts`
- `backend/src/services/stepQueue/instructorClient.ts`
- `backend/src/services/stepQueue/modelTier.ts`
- `backend/src/services/stepQueue/types.ts`

### backend/src/services/stepQueue/handlers/
- `backend/src/services/stepQueue/handlers/dailyBrief.ts`
- `backend/src/services/stepQueue/handlers/debate.ts`
- `backend/src/services/stepQueue/handlers/fundamentals.ts`
- `backend/src/services/stepQueue/handlers/macro.ts`
- `backend/src/services/stepQueue/handlers/quickCheck.ts`
- `backend/src/services/stepQueue/handlers/risk.ts`
- `backend/src/services/stepQueue/handlers/sentiment.ts`
- `backend/src/services/stepQueue/handlers/synthesis.ts`
- `backend/src/services/stepQueue/handlers/technical.ts`

### backend/src/types/
- `backend/src/types/index.ts`

### data/
- `data/config.json`
- `data/model-profiles.json`
- `data/portfolio.json`
- `data/support-messages.json`
- `data/system-agent.json`
- `data/system-control.json`

### db/
- `db/application_postgres.sql`

### docs/
- `docs/README.md`

### docs/archive/open-bugs/
- `docs/archive/open-bugs/full-report-schema-validation-failure.md`
- `docs/archive/open-bugs/onboarding-flow-gaps.md`
- `docs/archive/open-bugs/v2-deploy-bugs.md`
- `docs/archive/open-bugs/v3-deploy-bugs.md`
- `docs/archive/open-bugs/v4-deploy-bugs.md`
- `docs/archive/open-bugs/v5-deploy-bugs.md`

### docs/archive/production-reports/
- `docs/archive/production-reports/how-to-deploy-v2.md`
- `docs/archive/production-reports/migrations.md`
- `docs/archive/production-reports/phase-0-bugfix.md`
- `docs/archive/production-reports/phase-1-postgres-foundation.md`
- `docs/archive/production-reports/phase-2-step-queue.md`
- `docs/archive/production-reports/phase-3-openclaw-retirement.md`
- `docs/archive/production-reports/phase-3-review-fixes.md`
- `docs/archive/production-reports/phase-4-structured-outputs.md`
- `docs/archive/production-reports/phase-5-chat-agent.md`
- `docs/archive/production-reports/phase-6-transports.md`
- `docs/archive/production-reports/phase-7-ledger-snooze-dispatch.md`
- `docs/archive/production-reports/phase-v3-bugfixes.md`

### docs/archive/root-agent-docs/
- `docs/archive/root-agent-docs/CLAUDE.md`
- `docs/archive/root-agent-docs/HEARTBEAT.md`
- `docs/archive/root-agent-docs/RESET.md`
- `docs/archive/root-agent-docs/SOUL.md`

### docs/gsd-docs/
- `docs/gsd-docs/README.md`

### docs/gsd-docs/postgres-owned-product-state-migration/
- `docs/gsd-docs/postgres-owned-product-state-migration/implementation-brief.md`
- `docs/gsd-docs/postgres-owned-product-state-migration/README.md`
- `docs/gsd-docs/postgres-owned-product-state-migration/slice-execution-map.md`
- `docs/gsd-docs/postgres-owned-product-state-migration/verification-and-handoff.md`

### docs/gsd-docs/postgres-owned-product-state-migration/source-artifacts/
- `docs/gsd-docs/postgres-owned-product-state-migration/source-artifacts/DECISIONS.md`
- `docs/gsd-docs/postgres-owned-product-state-migration/source-artifacts/M001-ROADMAP.md`
- `docs/gsd-docs/postgres-owned-product-state-migration/source-artifacts/REQUIREMENTS.md`
- `docs/gsd-docs/postgres-owned-product-state-migration/source-artifacts/STATE.md`

### docs/pilot-features/
- `docs/pilot-features/pilot-core.json`
- `docs/pilot-features/README.md`

### docs/product/
- `docs/product/overview.md`

### frontend/
- `frontend/.gitignore`
- `frontend/eslint.config.js`
- `frontend/index.html`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/README.md`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`

### frontend/src/
- `frontend/src/App.css`
- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/main.tsx`

### frontend/src/api/
- `frontend/src/api/admin.ts`
- `frontend/src/api/analystConfig.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/api/balance.ts`
- `frontend/src/api/channels.ts`
- `frontend/src/api/chat.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/control.ts`
- `frontend/src/api/jobs.ts`
- `frontend/src/api/notifications.ts`
- `frontend/src/api/onboarding.ts`
- `frontend/src/api/portfolio.ts`
- `frontend/src/api/portfolioRisk.ts`
- `frontend/src/api/search.ts`
- `frontend/src/api/strategies.ts`
- `frontend/src/api/support.ts`

### frontend/src/components/
- `frontend/src/components/AnalystPipelineConfig.tsx`
- `frontend/src/components/ChannelConnectCode.tsx`
- `frontend/src/components/ControlBanner.tsx`
- `frontend/src/components/ImpersonationBanner.tsx`

### frontend/src/components/design/
- `frontend/src/components/design/ActionBadge.tsx`
- `frontend/src/components/design/HeroStatCard.tsx`
- `frontend/src/components/design/ScoreChip.tsx`
- `frontend/src/components/design/StatCell.tsx`

### frontend/src/components/jobs/
- `frontend/src/components/jobs/JobCard.tsx`
- `frontend/src/components/jobs/SupersededJobBanner.tsx`

### frontend/src/components/portfolio/
- `frontend/src/components/portfolio/AddPositionModal.tsx`
- `frontend/src/components/portfolio/PortfolioRiskCard.tsx`
- `frontend/src/components/portfolio/PositionDetailModal.tsx`
- `frontend/src/components/portfolio/PositionRow.tsx`
- `frontend/src/components/portfolio/StrategyModal.tsx`

### frontend/src/components/support/
- `frontend/src/components/support/ContactAdminButton.tsx`

### frontend/src/components/today/
- `frontend/src/components/today/AttentionCard.tsx`
- `frontend/src/components/today/SetupBanner.tsx`

### frontend/src/components/ui/
- `frontend/src/components/ui/Badge.tsx`
- `frontend/src/components/ui/BottomNav.tsx`
- `frontend/src/components/ui/Card.tsx`
- `frontend/src/components/ui/EmptyState.tsx`
- `frontend/src/components/ui/ErrorState.tsx`
- `frontend/src/components/ui/PointsBadge.tsx`
- `frontend/src/components/ui/Spinner.tsx`
- `frontend/src/components/ui/TickerSearch.tsx`
- `frontend/src/components/ui/Toast.tsx`

### frontend/src/pages/
- `frontend/src/pages/Admin.tsx`
- `frontend/src/pages/Alerts.tsx`
- `frontend/src/pages/Chat.tsx`
- `frontend/src/pages/Controls.tsx`
- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/Onboarding.tsx`
- `frontend/src/pages/Portfolio.tsx`
- `frontend/src/pages/Reports.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/Strategies.tsx`
- `frontend/src/pages/SuspensionPage.tsx`

### frontend/src/store/
- `frontend/src/store/authStore.ts`
- `frontend/src/store/i18n.ts`
- `frontend/src/store/impersonationStore.ts`
- `frontend/src/store/preferencesStore.ts`
- `frontend/src/store/toastStore.ts`

### frontend/src/types/
- `frontend/src/types/api.ts`

### frontend/src/utils/
- `frontend/src/utils/advisory.ts`
- `frontend/src/utils/format.ts`
- `frontend/src/utils/id.ts`

### frontend/src/utils/today/
- `frontend/src/utils/today/classifyAttention.ts`
- `frontend/src/utils/today/healthScore.ts`
- `frontend/src/utils/today/positionSubLine.ts`
- `frontend/src/utils/today/scoreColor.ts`
- `frontend/src/utils/today/whyToday.ts`

### scripts/
- `scripts/verify-advisory-readability.mjs`
- `scripts/verify-impersonation-policy.mjs`
- `scripts/verify-pilot-surface.mjs`
- `scripts/verify-saved-chat-ui.mjs`

### shared/user-workspace/
- `shared/user-workspace/manifest.json`
- `shared/user-workspace/README.md`
- `shared/user-workspace/USER.md.template`
