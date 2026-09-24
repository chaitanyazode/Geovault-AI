/**
 * GeoVault AI - Frontend TypeScript Definitions
 * Strictly mirrors backend schemas from Phase 4 through Phase 6B.
 */

export interface UserContext {
  user_id: string;
  username: string;
  full_name: string;
  email: string;
  role: string;
  department: string;
  clearance_level: "PUBLIC" | "INTERNAL" | "RESTRICTED" | "CONFIDENTIAL";
  subsidiary_code?: string;
  assigned_mine_code?: string;
  is_active: boolean;
}

export interface AuthorizedScope {
  user_id: string;
  role: string;
  department?: string;
  allowed_departments?: string[] | string;
  clearance_level?: string;
  clearance_rank?: number;
  max_clearance?: string;
  allowed_mines: string[] | string | null; // string[] when restricted, "ALL" when unrestricted
  is_national_authorized?: boolean;
  can_access_macro?: boolean;
}

/**
 * Normalizes allowed_mines (which can be a string[] from scoped users,
 * or "ALL" from enterprise/admin users) into a safe string[].
 */
export function normalizeAllowedMines(
  allowedMines: string[] | string | null | undefined
): string[] {
  if (!allowedMines) return [];
  if (Array.isArray(allowedMines)) return allowedMines;
  if (typeof allowedMines === "string") {
    const trimmed = allowedMines.trim();
    return trimmed ? [trimmed] : [];
  }
  return [];
}

/**
 * Checks if the user has unrestricted enterprise-wide mine scope.
 */
export function isEnterpriseScope(
  allowedMines: string[] | string | null | undefined
): boolean {
  if (!allowedMines) return false;
  if (typeof allowedMines === "string") {
    return allowedMines.toUpperCase() === "ALL";
  }
  if (Array.isArray(allowedMines)) {
    return allowedMines.length === 1 && allowedMines[0].toUpperCase() === "ALL";
  }
  return false;
}

/**
 * Formats scope for human-readable display in headers, cards, and tooltips.
 */
export function formatScopeMines(
  allowedMines: string[] | string | null | undefined,
  assignedMineCode?: string | null
): string {
  if (assignedMineCode) {
    return `Mine ${assignedMineCode}`;
  }
  if (isEnterpriseScope(allowedMines)) {
    return "ALL (Enterprise Scope)";
  }
  const list = normalizeAllowedMines(allowedMines);
  if (list.length === 0) return "None";
  return list.join(", ");
}

export interface UserProfileResponse {
  user: UserContext;
  scope: AuthorizedScope;
  authorized_scope?: AuthorizedScope;
}

export interface DemoUserOption {
  user_id: string;
  name: string;
  role: string;
  department: string;
  assigned_mine: string | null;
  clearance: string;
  description: string;
}

export interface EvidenceItem {
  evidence_id: string;
  source_type: string;
  source_name?: string;
  document_id?: string;
  document_name?: string;
  document_type?: "pdf" | "xlsx" | "image" | "document" | "spatial" | string;
  page_number?: number;
  page_count?: number;
  chunk_id?: string;
  mine_code?: string;
  department?: string;
  classification?: string;
  status?: string;
  source_text?: string;
  highlight_text?: string;
  sheet_name?: string | null;
  cell_range?: string | null;
  file_available?: boolean;
  can_stream_document?: boolean;
  snippet?: string;
  citation?: string;
  confidence_score?: number;
  page_text?: string;
  bounding_box?: number[] | null;
  layer_name?: string;
  feature_id?: string;
  geometry_type?: string;
  coordinates?: { longitude: number; latitude: number };
  distance_meters?: number;
  operation?: string;
  provenance_type?: string;
  spatial_metadata?: Record<string, any>;
  table_data?: {
    headers: string[];
    rows: Array<{ cells: string[]; is_highlighted?: boolean }>;
  } | null;
}

export interface ConflictItem {
  conflict_id: string;
  mine_code?: string;
  metric_or_topic: string;
  source_a_type: string;
  source_a_reference?: string;
  source_a_value: string;
  source_b_type: string;
  source_b_reference?: string;
  source_b_value: string;
  status: string;
  resolution_policy: string;
}

export interface DataGapItem {
  domain: string;
  mine_code?: string;
  year?: number;
  metric_key?: string;
  gap_type: string;
  description: string;
}

export type QueryType =
  | "STRUCTURED"
  | "SQL"
  | "ANALYTICS"
  | "RAG"
  | "SPATIAL"
  | "GEOLOGY"
  | "HYBRID"
  | "REPORT"
  | "TOPIC";

export type ConfidenceStatus =
  | "HIGH"
  | "GROUNDED"
  | "VERIFIED"
  | "PARTIAL"
  | "PARTIAL_GROUNDING"
  | "CONFLICT_DETECTED"
  | "INSUFFICIENT_DATA"
  | "INSUFFICIENT_AUTHORIZED_DATA";

export interface GroundedQueryResponse {
  query: string;
  query_type: QueryType;
  target_mine?: string;
  target_year?: number;
  answer: string;
  summary?: string;
  detailed_answer?: string;
  confidence_score?: number;
  confidence_status: ConfidenceStatus;
  validation_status: "VERIFIED" | "PARTIAL" | "CONFLICT" | "INSUFFICIENT_AUTHORIZED_DATA" | string;
  evidence: EvidenceItem[];
  conflicts: ConflictItem[];
  data_gaps: DataGapItem[];
  structured_results?: Record<string, any>;
  processing_metadata?: {
    orchestrator_version?: string;
    route_selected?: string;
    orchestration_latency_ms?: number;
    reasoner_latency_ms?: number;
    llm_latency_ms?: number;
    total_latency_ms?: number;
    user_id?: string;
    allowed_mines?: string[] | string;
    [key: string]: any;
  };
}

export interface ProductionAnnualRecord {
  production_id: string;
  mine_code: string;
  year: number;
  actual_production_mt: number;
  target_mt: number;
  variance_mt?: number;
  achievement_pct?: number;
  dispatch_mt?: number;
  equipment_or_face_availability_pct?: number;
}

export interface MineComparisonItem {
  mine_code: string;
  mine_name: string;
  year: number;
  actual_production_mt: number;
  target_production_mt: number;
  achievement_pct: number;
  variance_mt: number;
}

export interface QueryResultPackage {
  domain: string;
  query_description: string;
  authorized_scope_applied: Record<string, any>;
  facts: Record<string, any>[];
  analytics?: {
    operation?: string;
    metric?: string;
    total?: number;
    average?: number;
    min_value?: number;
    max_value?: number;
    target_achievement_pct?: number;
    variance_mt?: number;
    comparisons?: MineComparisonItem[];
    trend?: {
      points: { period: string | number; value: number; target?: number; delta?: number; growth_pct?: number }[];
      net_change: number;
      net_growth_pct: number;
      trajectory: "UPWARD" | "DOWNWARD" | "FLAT" | "FLUCTUATING";
      periods_count: number;
    };
  };
  evidence: EvidenceItem[];
  validation: {
    is_valid: boolean;
    evidence_status: string;
    math_checks: any[];
    detected_conflicts: ConflictItem[];
    data_gaps: DataGapItem[];
  };
}

export interface TopicKeywordItem {
  keyword: string;
  tfidf_score: number;
  frequency: number;
  document_count: number;
  rank: number;
}

export interface DiscoveredTopicItem {
  topic_id: string | number;
  title: string;
  chunk_count: number;
  document_chunk_count?: number;
  percentage_of_corpus: number;
  top_keywords: string[];
  representative_excerpts: string[];
  representative_quotes?: string[];
  mines_covered?: string[];
  description: string;
}

export interface TopicResponse {
  total_chunks_analyzed: number;
  total_documents_analyzed?: number;
  vocabulary_size: number;
  scope_applied: {
    user_id?: string;
    role?: string;
    clearance?: string;
    user_mines?: string[] | string;
    mine_filter?: string | null;
    department_filter?: string | null;
    year_filter?: number | null;
    [key: string]: any;
  };
  keywords: TopicKeywordItem[];
  topics: DiscoveredTopicItem[];
  wordcloud_url?: string;
  wordcloud_path?: string;
  wordcloud_file?: string;
  processing_time_ms: number;
  cached: boolean;
}

export function normalizeTopicResponse(raw: any): TopicResponse {
  if (!raw || typeof raw !== "object") {
    return {
      total_chunks_analyzed: 0,
      total_documents_analyzed: 0,
      vocabulary_size: 0,
      scope_applied: {},
      keywords: [],
      topics: [],
      processing_time_ms: 0,
      cached: false,
    };
  }

  const totalChunks = Number(raw.total_chunks_analyzed ?? 0);
  const safeTotalChunks = Number.isFinite(totalChunks) && totalChunks > 0 ? totalChunks : 0;

  const rawTopics = Array.isArray(raw.topics) ? raw.topics : [];
  const normalizedTopics: DiscoveredTopicItem[] = rawTopics.map((t: any, idx: number) => {
    // Backend intentionally provides document_chunk_count
    const rawCount = t?.chunk_count ?? t?.document_chunk_count ?? 0;
    const chunkCountNum = Number(rawCount);
    const chunk_count = Number.isFinite(chunkCountNum) && chunkCountNum >= 0 ? chunkCountNum : 0;

    // Backend does not send percentage_of_corpus; derive accurately from chunk_count / totalChunks
    let pct: number;
    if (t?.percentage_of_corpus !== undefined && t?.percentage_of_corpus !== null) {
      const parsed = Number(t.percentage_of_corpus);
      pct = Number.isFinite(parsed) ? parsed : 0;
    } else if (safeTotalChunks > 0) {
      pct = (chunk_count / safeTotalChunks) * 100;
    } else {
      pct = 0;
    }
    const safePercentage = Number.isFinite(pct) ? Math.max(0, Math.min(100, pct)) : 0;

    // Backend intentionally provides representative_quotes; map to representative_excerpts
    const rawQuotes = t?.representative_quotes ?? t?.representative_excerpts ?? [];
    const excerpts = Array.isArray(rawQuotes) ? rawQuotes.map((q: any) => String(q ?? "")) : [];

    // Keywords
    const rawKeywords = t?.top_keywords ?? t?.keywords ?? [];
    const top_keywords = Array.isArray(rawKeywords) ? rawKeywords.map((k: any) => String(k ?? "")) : [];

    return {
      topic_id: String(t?.topic_id ?? `TOPIC-${idx + 1}`),
      title: String(t?.title ?? `Topic ${idx + 1}`),
      chunk_count,
      document_chunk_count: chunk_count,
      percentage_of_corpus: safePercentage,
      top_keywords,
      representative_excerpts: excerpts,
      representative_quotes: excerpts,
      mines_covered: Array.isArray(t?.mines_covered) ? t.mines_covered : [],
      description: String(t?.description ?? ""),
    };
  });

  const rawKeywords = Array.isArray(raw.keywords) ? raw.keywords : [];
  const normalizedKeywords: TopicKeywordItem[] = rawKeywords.map((k: any, idx: number) => {
    const tfidf = Number(k?.tfidf_score ?? 0);
    const freq = Number(k?.frequency ?? 0);
    const docs = Number(k?.document_count ?? 0);
    const rnk = Number(k?.rank ?? idx + 1);

    return {
      keyword: String(k?.keyword ?? ""),
      tfidf_score: Number.isFinite(tfidf) ? tfidf : 0,
      frequency: Number.isFinite(freq) ? freq : 0,
      document_count: Number.isFinite(docs) ? docs : 0,
      rank: Number.isFinite(rnk) ? rnk : idx + 1,
    };
  });

  const rawTime = Number(raw.processing_time_ms ?? 0);
  const processing_time_ms = Number.isFinite(rawTime) ? rawTime : 0;

  return {
    total_chunks_analyzed: safeTotalChunks,
    total_documents_analyzed: Number(raw.total_documents_analyzed ?? 0) || 0,
    vocabulary_size: Number(raw.vocabulary_size ?? normalizedKeywords.length) || normalizedKeywords.length,
    scope_applied: raw.scope_applied && typeof raw.scope_applied === "object" ? raw.scope_applied : {},
    keywords: normalizedKeywords,
    topics: normalizedTopics,
    wordcloud_url: raw.wordcloud_url ? String(raw.wordcloud_url) : undefined,
    wordcloud_path: raw.wordcloud_path ? String(raw.wordcloud_path) : undefined,
    wordcloud_file: raw.wordcloud_file ? String(raw.wordcloud_file) : undefined,
    processing_time_ms,
    cached: Boolean(raw.cached),
  };
}

export interface ReportMetadataResponse {
  report_id: string;
  report_title: string;
  report_type: string;
  mine_code?: string;
  mines_covered: string[];
  reporting_period: string;
  generated_at: string;
  requested_by: string;
  status: string;
  output_formats: string[];
  docx_download_url: string;
  pdf_download_url: string;
  evidence_count: number;
  conflict_count: number;
  data_gap_count: number;
  validation_status: string;
  executive_summary?: string;
  production_annual?: Array<{
    mine_code: string;
    year: number;
    target_mt: number;
    actual_production_mt: number;
    achievement_pct: number;
    obr_mm3?: number;
    target_obr_mm3?: number;
    actual_obr_mm3?: number;
  }>;
  evidence_citations?: Array<{
    evidence_id?: string;
    source_type?: string;
    document_id?: string;
    page_number?: number;
    source_text?: string;
    sheet_name?: string;
    cell_range?: string;
  }>;
  key_indicators?: Array<{
    metric: string;
    value: string;
    source: string;
  }>;
}

export interface SystemHealth {
  status: string;
  backend: string;
  postgres: string;
  redis: string;
  llm: string;
  timestamp: string;
}

export interface AuditLogItem {
  log_id: string;
  user_id: string;
  time?: string | null;
  timestamp?: string | null;
  action: string;
  module: string;
  route: string;
  details?: string;
  sanitized_details?: string;
  status: "Success" | "Denied" | "Discrepancy" | "Failed" | "SUCCESS" | "DENIED" | "DISCREPANCY" | "ERROR" | string;
  evidence_status?: string | null;
  evidence_count: number;
  execution_time_ms?: number | null;
  mine_scope?: string[];
  report_id?: string | null;
  correlation_id?: string | null;
  http_status?: number;
}

export interface AuditLogSummary {
  total_events: number;
  successful_events: number;
  discrepancy_events: number;
  denied_events: number;
  report_events: number;
  avg_latency_ms?: number | null;
  authorized_mines_covered: string[];
}

export interface AuditLogPaginatedResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
