/**
 * GeoVault AI - Type-Safe Enterprise API Client
 * Centralizes request execution, X-User-ID header injection,
 * response serialization, and 403 Forbidden extraction.
 */

import {
  UserProfileResponse,
  DemoUserOption,
  GroundedQueryResponse,
  QueryResultPackage,
  TopicResponse,
  TopicKeywordItem,
  ReportMetadataResponse,
  ConflictItem,
  EvidenceItem,
  SystemHealth,
  normalizeTopicResponse,
  AuditLogItem,
  AuditLogSummary,
  AuditLogPaginatedResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const getApiBase = (): string => API_BASE;

// Default active demo user
let currentUserId = "USR001";

export const getActiveUserId = (): string => currentUserId;

export const setActiveUserId = (userId: string): void => {
  currentUserId = userId;
  if (typeof window !== "undefined") {
    localStorage.setItem("geovault_user_id", userId);
  }
};

// Initialize from localStorage if client-side
if (typeof window !== "undefined") {
  const stored = localStorage.getItem("geovault_user_id");
  if (stored) {
    currentUserId = stored;
  }
}

export class ApiError extends Error {
  status: number;
  detail: string;
  isAccessDenied: boolean;

  constructor(status: number, detail: string) {
    super(detail || `API Request failed with HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.isAccessDenied = status === 403;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = new Headers(options.headers || {});

  // Inject authoritative identity header
  if (!headers.has("X-User-ID")) {
    headers.set("X-User-ID", currentUserId);
  }

  if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let detail = `Error ${res.status}`;
      try {
        const errorJson = await res.json();
        detail = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        detail = await res.text();
      }
      throw new ApiError(res.status, detail);
    }

    return (await res.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(500, err.message || "Network connection error");
  }
}

export const ApiClient = {
  // ---------------------------------------------------------------------------
  // 1. Identity & Scope
  // ---------------------------------------------------------------------------
  getUsers: async (): Promise<DemoUserOption[]> => {
    const res = await request<DemoUserOption[] | { users: DemoUserOption[] }>("/api/v1/auth/users");
    return Array.isArray(res) ? res : (res as any).users || [];
  },

  getUserProfile: async (): Promise<UserProfileResponse> => {
    return request<UserProfileResponse>("/api/v1/auth/me");
  },

  // ---------------------------------------------------------------------------
  // 2. Natural Query & AI Orchestration (Ask GeoVault)
  // ---------------------------------------------------------------------------
  executeNaturalQuery: async (
    query: string,
    targetMine?: string,
    targetYear?: number
  ): Promise<GroundedQueryResponse> => {
    return request<GroundedQueryResponse>("/api/v1/intelligence/natural-query", {
      method: "POST",
      body: JSON.stringify({
        query,
        target_mine: targetMine || null,
        target_year: targetYear || null,
      }),
    });
  },

  // ---------------------------------------------------------------------------
  // 3. Operational Data & Deterministic Analytics (Dashboard)
  // ---------------------------------------------------------------------------
  getAnnualProduction: async (
    mineCode?: string,
    startYear: number = 2021,
    endYear: number = 2025
  ): Promise<QueryResultPackage> => {
    return request<QueryResultPackage>("/api/v1/intelligence/query", {
      method: "POST",
      body: JSON.stringify({
        domain: "production_annual",
        mine_code: mineCode || null,
        start_year: startYear,
        end_year: endYear,
      }),
    });
  },

  compareMines: async (
    mineCodes: string[] = [],
    startYear: number = 2021,
    endYear: number = 2025
  ): Promise<QueryResultPackage> => {
    return request<QueryResultPackage>("/api/v1/intelligence/compare", {
      method: "POST",
      body: JSON.stringify({
        mine_codes: mineCodes.length > 0 ? mineCodes : null,
        start_year: startYear,
        end_year: endYear,
      }),
    });
  },

  getMiningIssues: async (mineCode?: string): Promise<QueryResultPackage> => {
    return request<QueryResultPackage>("/api/v1/intelligence/query", {
      method: "POST",
      body: JSON.stringify({
        domain: "mining_issue_log",
        mine_code: mineCode || null,
      }),
    });
  },

  // ---------------------------------------------------------------------------
  // 4. Topic Analysis & Word Cloud
  // ---------------------------------------------------------------------------
  analyzeTopics: async (
    mineCode?: string,
    department?: string,
    year?: number
  ): Promise<TopicResponse> => {
    const raw = await request<any>("/api/v1/topics/analyze", {
      method: "POST",
      body: JSON.stringify({
        mine_code: mineCode || null,
        department: department || null,
        year: year || null,
        num_clusters: 4,
        max_keywords: 25,
      }),
    });
    return normalizeTopicResponse(raw);
  },

  getTopKeywords: async (mineCode?: string, limit: number = 15): Promise<TopicKeywordItem[]> => {
    const params = new URLSearchParams();
    if (mineCode) params.set("mine_code", mineCode);
    params.set("limit", limit.toString());
    return request<TopicKeywordItem[]>(`/api/v1/topics/keywords?${params.toString()}`);
  },

  getWordCloudImageUrl: (filename: string): string => {
    return `${API_BASE}/api/v1/topics/wordcloud/image/${filename}`;
  },

  // ---------------------------------------------------------------------------
  // 5. Report Generator
  // ---------------------------------------------------------------------------
  generateReport: async (payload: {
    query?: string;
    mine_code?: string;
    compared_mines?: string[];
    start_year?: number;
    end_year?: number;
    report_type?: string;
    include_charts?: boolean;
  }): Promise<ReportMetadataResponse> => {
    return request<ReportMetadataResponse>("/api/v1/reports/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getReportMetadata: async (reportId: string): Promise<ReportMetadataResponse> => {
    return request<ReportMetadataResponse>(`/api/v1/reports/${reportId}`);
  },

  getReportDownloadUrl: (reportId: string, format: "pdf" | "docx"): string => {
    return `${API_BASE}/api/v1/reports/${reportId}/download/${format}`;
  },

  downloadReportFile: async (reportId: string, format: "pdf" | "docx"): Promise<Blob> => {
    const url = `${API_BASE}/api/v1/reports/${reportId}/download/${format}`;
    const res = await fetch(url, {
      headers: { "X-User-ID": currentUserId },
    });
    if (!res.ok) {
      let detail = `Error ${res.status}`;
      try {
        const errorJson = await res.json();
        detail = errorJson.detail || detail;
      } catch {
        // use default
      }
      throw new ApiError(res.status, detail);
    }
    return res.blob();
  },

  // ---------------------------------------------------------------------------
  // 6. Evidence & Discovered Conflicts
  // ---------------------------------------------------------------------------
  getConflicts: async (): Promise<ConflictItem[]> => {
    return request<ConflictItem[]>("/api/v1/conflicts");
  },

  getEvidenceItem: async (evidenceId: string): Promise<EvidenceItem> => {
    return request<EvidenceItem>(`/api/v1/evidence/${evidenceId}`);
  },

  // ---------------------------------------------------------------------------
  // 7. System Health
  // ---------------------------------------------------------------------------
  getHealth: async (): Promise<SystemHealth> => {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) {
      throw new Error(`Health check failed with ${res.status}`);
    }
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // 8. Governance & Operational Logs (Phase 5F)
  // ---------------------------------------------------------------------------
  getAuditLogs: async (limit: number = 50): Promise<AuditLogItem[]> => {
    return request<AuditLogItem[]>(`/api/v1/intelligence/logs?limit=${limit}`);
  },

  getAuditLogsPaged: async (params: {
    page?: number;
    page_size?: number;
    mine?: string;
    action?: string;
    status?: string;
    user_id?: string;
    search?: string;
    start_date?: string;
    end_date?: string;
    log_access?: boolean;
  } = {}): Promise<AuditLogPaginatedResponse> => {
    const query = new URLSearchParams();
    if (params.page) query.set("page", params.page.toString());
    if (params.page_size) query.set("page_size", params.page_size.toString());
    if (params.mine) query.set("mine", params.mine);
    if (params.action) query.set("action", params.action);
    if (params.status) query.set("status", params.status);
    if (params.user_id) query.set("user_id", params.user_id);
    if (params.search) query.set("search", params.search);
    if (params.start_date) query.set("start_date", params.start_date);
    if (params.end_date) query.set("end_date", params.end_date);
    if (params.log_access) query.set("log_access", "true");
    const qs = query.toString();
    return request<AuditLogPaginatedResponse>(`/api/v1/audit-logs/${qs ? `?${qs}` : ""}`);
  },

  getAuditSummary: async (mine?: string): Promise<AuditLogSummary> => {
    const qs = mine ? `?mine=${encodeURIComponent(mine)}` : "";
    return request<AuditLogSummary>(`/api/v1/audit-logs/summary${qs}`);
  },

  // ---------------------------------------------------------------------------
  // 9. Reports List (Phase 5E)
  // ---------------------------------------------------------------------------
  listReports: async (limit: number = 20): Promise<any[]> => {
    return request<any[]>(`/api/v1/reports/?limit=${limit}`);
  },

  // Generic GET helper for arbitrary authorized endpoints
  get: async <T = any>(path: string): Promise<T> => {
    return request<T>(`/api/v1${path}`);
  },
};
