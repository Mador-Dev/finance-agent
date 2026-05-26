from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


TickerPattern = r"^[A-Z0-9.]{1,12}$"
ConversationIdPattern = r"^[A-Za-z0-9_-]{1,64}$"

JobAction = Literal[
    "daily_brief",
    "full_report",
    "deep_dive",
    "new_ideas",
    "quick_check",
    "switch_production",
    "switch_testing",
]
JobStatus = Literal[
    "pending",
    "paused",
    "running",
    "completed",
    "partial_completed",
    "failed",
    "cancelled",
    "superseded",
]
Verdict = Literal["BUY", "ADD", "HOLD", "REDUCE", "SELL", "CLOSE"]
Confidence = Literal["high", "medium", "low"]
JsonValue = Any


class ScheduleInput(BaseModel):
    dailyBriefTime: str = "08:00"
    weeklyResearchDay: str = "sunday"
    weeklyResearchTime: str = "19:00"
    timezone: str = "Asia/Jerusalem"


class PositionInput(BaseModel):
    ticker: str = Field(pattern=TickerPattern)
    exchange: Literal["TASE", "NYSE", "NASDAQ", "LSE", "XETRA", "EURONEXT", "OTHER"]
    shares: int = Field(gt=0)
    unitAvgBuyPrice: float = Field(gt=0)
    unitCurrency: Literal["USD", "ILA", "GBP", "EUR"]

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        return value.strip().upper()


class PositionGuidanceInput(BaseModel):
    thesis: str = Field(default="", max_length=400)
    horizon: Literal["unspecified", "days", "weeks", "months", "years"] = "unspecified"
    addOn: str = Field(default="", max_length=300)
    reduceOn: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=600)


class BootstrapStartRequest(BaseModel):
    userId: str = Field(min_length=1, max_length=64)
    displayName: str | None = Field(default=None, max_length=50)
    accounts: dict[str, list[PositionInput]]
    guidance: dict[str, PositionGuidanceInput] = Field(default_factory=dict)
    schedule: ScheduleInput = Field(default_factory=ScheduleInput)
    currency: Literal["ILS"] = "ILS"
    transactionFeeILS: float = 0
    note: str = ""

    @field_validator("accounts")
    @classmethod
    def require_accounts(cls, value: dict[str, list[PositionInput]]) -> dict[str, list[PositionInput]]:
        if not value:
            raise ValueError("At least one account is required")
        non_empty = {name: positions for name, positions in value.items() if positions}
        if not non_empty:
            raise ValueError("At least one position is required")
        return non_empty


class StrategyCatalyst(BaseModel):
    """A monitorable event the thesis depends on.

    The catalyst window is described by `windowStart` + `windowEnd`. The
    legacy `expiresAt` field is preserved so old rows still validate; new
    writers should populate `windowEnd` (UI treats `windowEnd ?? expiresAt`
    as the authoritative deadline).
    """

    description: str = Field(max_length=300)
    category: Literal[
        "earnings", "product", "regulatory", "macro", "guidance", "other"
    ] = "other"
    windowStart: str | None = None  # ISO date when the catalyst window opens
    windowEnd: str | None = None    # ISO date when it closes (preferred over expiresAt)
    importance: Literal["high", "medium", "low"] = "medium"
    expiresAt: str | None = None    # legacy alias for windowEnd (back-compat only)
    triggered: bool = False


class ResearchEvidence(BaseModel):
    supporting: list[str] = Field(default_factory=list)
    conflicting: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class CoordinatorDraft(BaseModel):
    """The strategy synthesis fields the coordinator LLM emits.

    Kept separate from `TickerStrategyDraft` for one reason: OpenAI strict
    structured-output mode rejects `dict[str, Any]` (it requires
    `additionalProperties:false` on every object). `analyst_reports` is filled
    programmatically by the LangGraph workflow after synthesis, so it doesn't
    need to be in the LLM's response schema.
    """

    ticker: str = Field(pattern=TickerPattern)
    thesis: str = Field(max_length=280)
    verdict: Verdict
    confidence: Confidence
    catalysts: list[StrategyCatalyst] = Field(default_factory=list, max_length=10)
    timeframe: Literal["week", "months", "years", "long_term", "undefined"] = "months"
    bull_case: str | None = Field(default=None, max_length=600)
    bear_case: str | None = Field(default=None, max_length=600)
    key_risks: list[str] = Field(default_factory=list, max_length=8)
    invalidation_conditions: list[str] = Field(default_factory=list, max_length=8)
    entry_conditions: list[str] = Field(default_factory=list, max_length=5)
    evidence_summary: ResearchEvidence = Field(default_factory=ResearchEvidence)
    reasoning: str = Field(max_length=800)
    next_review_at: str | None = None


class TickerStrategyDraft(CoordinatorDraft):
    """Full strategy draft = coordinator synthesis + attached analyst reports."""

    # analyst_reports is filled by the workflow, never by the LLM directly.
    analyst_reports: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @classmethod
    def from_coordinator(
        cls, draft: "CoordinatorDraft", analyst_reports: dict[str, dict[str, Any]]
    ) -> "TickerStrategyDraft":
        return cls(**draft.model_dump(), analyst_reports=analyst_reports)


# ── Structured analyst report payloads ──────────────────────────────────────
# Each report kind is a Pydantic model so the LangGraph workflow gets a strict
# schema for OpenAI structured outputs and so the DB row payload is consistent.


class Earnings(BaseModel):
    result: Literal["beat", "miss", "in_line"] | None = None
    epsActual: float | None = None
    epsExpected: float | None = None
    revenueActualM: float | None = None
    revenueExpectedM: float | None = None


class Valuation(BaseModel):
    pe: float | None = None
    fcfYield: float | None = None
    sectorAvgPe: float | None = None
    assessment: Literal["cheap", "fair", "expensive"] | None = None


class AnalystConsensus(BaseModel):
    buy: int = 0
    hold: int = 0
    sell: int = 0
    avgTargetPrice: float | None = None
    currency: Literal["USD", "ILS"] = "USD"


class FundamentalsReport(BaseModel):
    earnings: Earnings | None = None
    nextEarningsDate: str | None = None
    revenueGrowthYoY: float | None = None
    marginTrend: Literal["improving", "stable", "deteriorating"] | None = None
    guidance: Literal["raised", "maintained", "lowered", "unknown"] = "unknown"
    balanceSheet: Literal["strong", "adequate", "stretched"] | None = None
    debtToEquity: float | None = None
    valuation: Valuation | None = None
    analystConsensus: AnalystConsensus | None = None
    insiderActivity: Literal["buying", "selling", "neutral", "unknown"] = "unknown"
    fundamentalView: str = ""
    sources: list[str] = Field(default_factory=list)


class PriceContext(BaseModel):
    current: float | None = None
    week52Low: float | None = None
    week52High: float | None = None
    positionInRange: float | None = None


class MovingAverages(BaseModel):
    ma50: float | None = None
    ma200: float | None = None
    priceVsMa50: Literal["above", "below"] | None = None
    priceVsMa200: Literal["above", "below"] | None = None


class RSI(BaseModel):
    value: float | None = None
    signal: Literal["overbought", "neutral", "oversold"] | None = None


class KeyLevels(BaseModel):
    support: float | None = None
    resistance: float | None = None


class TechnicalReport(BaseModel):
    price: PriceContext | None = None
    movingAverages: MovingAverages | None = None
    rsi: RSI | None = None
    macd: Literal["bullish", "bearish", "neutral"] = "neutral"
    volume: Literal["elevated", "average", "low"] = "average"
    keyLevels: KeyLevels | None = None
    pattern: str | None = None
    atr: float | None = None
    trendStrength: Literal["uptrend", "downtrend", "sideways"] | None = None
    technicalView: str = ""
    sources: list[str] = Field(default_factory=list)


class AnalystAction(BaseModel):
    action: str
    analyst: str
    targetPrice: float | None = None


class InsiderTransaction(BaseModel):
    type: Literal["Buy", "Sell"]
    insider: str
    shares: str | None = None
    value: str | None = None


class NewsItem(BaseModel):
    headline: str
    sentiment: Literal["positive", "negative", "neutral"] = "neutral"
    url: str | None = None


class SentimentReport(BaseModel):
    analystActions: list[AnalystAction] = Field(default_factory=list)
    insiderTransactions: list[InsiderTransaction] = Field(default_factory=list)
    majorNews: list[NewsItem] = Field(default_factory=list)
    shortInterest: str | None = None
    optionsFlow: Literal["bullish", "bearish", "neutral"] | None = None
    institutionalChangeSummary: str | None = None
    narrativeShift: str = ""
    sentimentView: str = ""
    sources: list[str] = Field(default_factory=list)


class RateEnvironment(BaseModel):
    relevantBank: str = ""
    currentRate: str = ""
    direction: Literal["hiking", "cutting", "holding"] = "holding"
    relevance: str = ""


class SectorPerformance(BaseModel):
    sectorName: str = ""
    performanceVsMarket30d: str = ""
    trend: Literal["outperforming", "in_line", "underperforming"] = "in_line"


class CurrencyEnv(BaseModel):
    usdIls: str | None = None
    trend: Literal["strengthening", "stable", "weakening"] = "stable"
    impactOnPosition: str = ""


class Geopolitical(BaseModel):
    relevantFactor: str | None = None
    riskLevel: Literal["low", "medium", "high"] | None = None


class MacroReport(BaseModel):
    rateEnvironment: RateEnvironment | None = None
    sectorPerformance: SectorPerformance | None = None
    currency: CurrencyEnv | None = None
    geopolitical: Geopolitical | None = None
    inflationRead: Literal["cooling", "sticky", "rising"] | None = None
    marketRegime: str = ""
    macroView: str = ""
    sources: list[str] = Field(default_factory=list)


class RiskReport(BaseModel):
    portfolioWeightPct: float | None = None
    positionValueILS: float | None = None
    plPct: float | None = None
    plILS: float | None = None
    avgPricePaid: str | None = None
    livePriceCurrency: Literal["USD", "ILS"] | None = None
    concentrationFlag: bool = False
    stopLossLevel: float | None = None
    maxDrawdownFromEntryPct: float | None = None
    riskFacts: str = ""
    sources: list[str] = Field(default_factory=list)


class CaseArgument(BaseModel):
    claim: str = Field(max_length=200)
    dataPoint: str = ""


class BullCaseReport(BaseModel):
    coreThesis: str
    priceTarget12m: float | None = None
    probabilityEstimate: int | None = None
    arguments: list[CaseArgument] = Field(default_factory=list)
    conditionToBeWrong: str = ""
    sources: list[str] = Field(default_factory=list)


class BearCaseReport(BaseModel):
    coreConcern: str
    priceTarget12m: float | None = None
    probabilityEstimate: int | None = None
    arguments: list[CaseArgument] = Field(default_factory=list)
    conditionToBeWrong: str = ""
    sources: list[str] = Field(default_factory=list)


class DebateReport(BaseModel):
    resolution: str
    confidenceModifier: Literal["+1 notch", "unchanged", "-1 notch"] = "unchanged"
    keySwingFactor: str = ""
    verdictChange: str | None = None
    baseCasePriceTarget: float | None = None


class CatalystExpiryCheck(BaseModel):
    expiredCount: int = 0
    nearingExpiry: list[str] = Field(default_factory=list)


class QuickCheckReport(BaseModel):
    score: int = Field(ge=0, le=100)
    decision: Literal["safe", "watch", "escalate"]
    signals: list[str] = Field(default_factory=list)
    thesisHealth: list[str] = Field(default_factory=list)
    catalystExpiryCheck: CatalystExpiryCheck = Field(default_factory=CatalystExpiryCheck)
    thesisAlignmentFlag: Literal["aligned", "neutral", "diverging"] = "neutral"
    escalationReason: str | None = None
    advisorSummary: str = ""
    advisorReasons: list[str] = Field(default_factory=list)
    dayChangePct: float | None = None
    newsHeadline: str | None = None
    daysSinceLastDeepDive: int | None = None
    sources: list[str] = Field(default_factory=list)


class DailyReport(BaseModel):
    moveReason: str = ""
    dayChangePct: float | None = None
    volumeFlag: Literal["normal", "elevated", "low"] = "normal"
    sectorChangePct: float | None = None
    relativeStrength: Literal["outperforming", "inline", "underperforming"] | None = None
    newsHeadline: str | None = None
    newsUrl: str | None = None
    escalationSignal: bool = False
    sources: list[str] = Field(default_factory=list)


class BootstrapTickerState(BaseModel):
    ticker: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    currentStep: str | None = None
    failureReason: str | None = None
    strategy: TickerStrategyDraft | None = None


class BootstrapJobState(BaseModel):
    jobId: str
    userId: str
    status: Literal["pending", "running", "completed", "failed", "partial_completed"] = "pending"
    createdAt: str
    startedAt: str | None = None
    completedAt: str | None = None
    progressPct: int = 0
    totalTickers: int
    completedTickers: list[str] = Field(default_factory=list)
    failedTickers: list[str] = Field(default_factory=list)
    currentTicker: str | None = None
    currentStep: str | None = None
    tickers: list[BootstrapTickerState]
    error: str | None = None


class BootstrapStartResponse(BaseModel):
    jobId: str
    status: str
    totalTickers: int


class BootstrapJobResult(BaseModel):
    jobId: str
    userId: str
    status: str
    strategies: list[TickerStrategyDraft]
    completedAt: str | None = None


class JobProgress(BaseModel):
    pct: int = 0
    currentTicker: str | None = None
    currentStep: str | None = None
    completedTickers: list[str] = Field(default_factory=list)
    remainingTickers: list[str] = Field(default_factory=list)
    totalTickers: int = 0
    completedSteps: int = 0
    totalSteps: int = 0


class JobRecord(BaseModel):
    id: str
    action: JobAction
    ticker: str | None = None
    status: JobStatus
    triggered_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: JsonValue = None
    error: str | None = None
    progress: JobProgress | None = None
    source: str | None = "dashboard_action"
    budget_admitted_at: str | None = None
    user_id: str | None = None
    tickers: list[str] = Field(default_factory=list)


class JobsResponse(BaseModel):
    jobs: list[JobRecord]


class TriggerJobRequest(BaseModel):
    action: JobAction
    ticker: str | None = None

    @field_validator("ticker")
    @classmethod
    def normalize_optional_ticker(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()


class TriggerResponse(BaseModel):
    jobId: str
    job: JobRecord


class ChatMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    conversationId: str | None = Field(default=None, pattern=ConversationIdPattern)


class ChatMessageResponse(BaseModel):
    conversationId: str
    replyText: str


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=160)


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class SavedConversation(BaseModel):
    id: str
    userId: str
    title: str | None = None
    createdAt: str


class ChatMemoryEntry(BaseModel):
    id: str
    conversationId: str
    sequenceNumber: int
    role: str
    content: str


class SavedConversationListResponse(BaseModel):
    items: list[SavedConversation]
    limit: int
    offset: int


class SavedConversationResponse(BaseModel):
    conversation: SavedConversation


class ConversationHistory(BaseModel):
    conversation: SavedConversation
    turns: list[ChatMemoryEntry]


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
