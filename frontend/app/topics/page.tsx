"use client";

import React, { useEffect, useState } from "react";
import {
  CloudSun,
  Filter,
  Layers,
  Hash,
  Download,
  ShieldCheck,
  Building,
  Quote,
  Calendar,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { ApiClient, ApiError, getApiBase } from "../../lib/api";
import {
  TopicResponse,
  UserProfileResponse,
  normalizeAllowedMines,
  isEnterpriseScope,
  normalizeTopicResponse,
} from "../../lib/types";
import AccessRestrictedAlert from "../../components/AccessRestrictedAlert";

// Canonical Mine Dictionary
const CANONICAL_MINES_DISPLAY: Record<string, { code: string; name: string }> = {
  GV001: { code: "GV001", name: "GEVRA" },
  GEVRA: { code: "GV001", name: "GEVRA" },
  GV002: { code: "GV002", name: "KUSMUNDA" },
  KUSMUNDA: { code: "GV002", name: "KUSMUNDA" },
  GV003: { code: "GV003", name: "DIPKA" },
  DIPKA: { code: "GV003", name: "DIPKA" },
  GV004: { code: "GV004", name: "NIGAHI" },
  NIGAHI: { code: "GV004", name: "NIGAHI" },
  GV005: { code: "GV005", name: "DUDHICHUA" },
  DUDHICHUA: { code: "GV005", name: "DUDHICHUA" },
};

const ALL_5_CANONICAL_MINES = [
  { code: "GV001", name: "GEVRA" },
  { code: "GV002", name: "KUSMUNDA" },
  { code: "GV003", name: "DIPKA" },
  { code: "GV004", name: "NIGAHI" },
  { code: "GV005", name: "DUDHICHUA" },
];

export default function TopicsPage() {
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [topicData, setTopicData] = useState<TopicResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [isAccessDenied, setIsAccessDenied] = useState(false);
  const [authorizedMines, setAuthorizedMines] = useState<Array<{ code: string; name: string }>>([]);

  // Filter form states
  const [mineFilter, setMineFilter] = useState<string>("");
  const [deptFilter, setDeptFilter] = useState<string>("");
  const [yearFilter, setYearFilter] = useState<string>("");

  const loadTopics = async (mine?: string, dept?: string, yr?: string) => {
    setLoading(true);
    setErrorDetail(null);
    setIsAccessDenied(false);

    try {
      const yrNum = yr ? parseInt(yr, 10) : undefined;
      const res = await ApiClient.analyzeTopics(
        mine || undefined,
        dept || undefined,
        yrNum
      );
      setTopicData(normalizeTopicResponse(res));
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403) {
        setIsAccessDenied(true);
        setErrorDetail(err.detail || "Access to this information is outside your authorized scope.");
      } else if (err instanceof ApiError) {
        setErrorDetail(err.detail || `Topic analysis service error (HTTP ${err.status}).`);
      } else {
        setErrorDetail(err.message || "Failed to analyze topics across authorized records.");
      }
      setTopicData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    ApiClient.getUserProfile().then((prof) => {
      setProfile(prof);
      const isAll = isEnterpriseScope(prof.scope.allowed_mines);

      let resolvedMines: Array<{ code: string; name: string }> = [];
      if (isAll) {
        resolvedMines = ALL_5_CANONICAL_MINES;
      } else {
        const rawList = normalizeAllowedMines(prof.scope.allowed_mines);
        const mapSeen = new Map<string, { code: string; name: string }>();

        for (const raw of rawList) {
          const matched = CANONICAL_MINES_DISPLAY[raw.toUpperCase()] || CANONICAL_MINES_DISPLAY[raw];
          if (matched && !mapSeen.has(matched.code)) {
            mapSeen.set(matched.code, matched);
          }
        }
        resolvedMines = Array.from(mapSeen.values());
      }

      setAuthorizedMines(resolvedMines);

      // Default filter selection based on user assignment
      let defaultMine = "";
      if (prof.user.assigned_mine_code) {
        const matched = CANONICAL_MINES_DISPLAY[prof.user.assigned_mine_code.toUpperCase()];
        if (matched) defaultMine = matched.code;
      }

      setMineFilter(defaultMine);
      loadTopics(defaultMine);
    });
  }, []);

  const handleApplyFilter = (e: React.FormEvent) => {
    e.preventDefault();
    loadTopics(mineFilter, deptFilter, yearFilter);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Topics &amp; Word Cloud
          </h1>
          <p className="text-sm sm:text-base text-slate-600 mt-1">
            Discover recurring themes and patterns across authorized mining and geological reports.
          </p>
        </div>

        {topicData && (
          <div className="flex items-center gap-2 text-sm text-slate-700 font-semibold">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200">
              <CheckCircle2 className="w-4 h-4 text-blue-900" />
              {Number(topicData.total_chunks_analyzed ?? 0)} Sections Analyzed
            </span>
          </div>
        )}
      </div>

      {/* Filter Control Bar: Strictly Scoped */}
      <form
        onSubmit={handleApplyFilter}
        className="bg-white border border-slate-200 p-5 rounded-xl shadow-xs flex flex-wrap items-end gap-4 text-sm"
      >
        {/* Mine Scope Filter: Displays only mines permitted for user */}
        <div className="space-y-1.5 min-w-48">
          <label className="text-slate-800 font-bold flex items-center gap-1.5 text-xs sm:text-sm">
            <Building className="w-4 h-4 text-blue-900" />
            Authorized Mine Scope
          </label>
          <select
            value={mineFilter}
            onChange={(e) => setMineFilter(e.target.value)}
            className="w-full bg-white border border-slate-300 rounded-lg px-3.5 py-2.5 text-slate-800 text-sm focus:outline-none focus:border-blue-900 cursor-pointer"
          >
            <option value="">All Authorized Mines</option>
            {authorizedMines.map((m) => (
              <option key={m.code} value={m.code}>
                {m.code} — {m.name}
              </option>
            ))}
          </select>
        </div>

        {/* Department Filter */}
        <div className="space-y-1.5 min-w-44">
          <label className="text-slate-800 font-bold flex items-center gap-1.5 text-xs sm:text-sm">
            <Layers className="w-4 h-4 text-blue-900" />
            Department
          </label>
          <select
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
            className="w-full bg-white border border-slate-300 rounded-lg px-3.5 py-2.5 text-slate-800 text-sm focus:outline-none focus:border-blue-900 cursor-pointer"
          >
            <option value="">All Departments</option>
            <option value="Mining">Mining Operations</option>
            <option value="Geology">Geology &amp; Strata</option>
            <option value="Safety">Safety &amp; Compliance</option>
            <option value="Transportation">Transportation &amp; Dispatch</option>
          </select>
        </div>

        {/* Reporting Year Filter */}
        <div className="space-y-1.5 min-w-40">
          <label className="text-slate-800 font-bold flex items-center gap-1.5 text-xs sm:text-sm">
            <Calendar className="w-4 h-4 text-blue-900" />
            Reporting Year
          </label>
          <select
            value={yearFilter}
            onChange={(e) => setYearFilter(e.target.value)}
            className="w-full bg-white border border-slate-300 rounded-lg px-3.5 py-2.5 text-slate-800 text-sm focus:outline-none focus:border-blue-900 cursor-pointer"
          >
            <option value="">All Years</option>
            <option value="2021">FY2021</option>
            <option value="2022">FY2022</option>
            <option value="2023">FY2023</option>
            <option value="2024">FY2024</option>
            <option value="2025">FY2025</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="px-5 py-2.5 rounded-lg bg-blue-900 hover:bg-blue-800 text-white font-bold text-sm flex items-center gap-2 transition disabled:opacity-50 sm:ml-auto shadow-xs cursor-pointer"
        >
          <Filter className="w-4 h-4" /> Apply Filter
        </button>
      </form>

      {/* Access Denied Alert */}
      {isAccessDenied && (
        <AccessRestrictedAlert
          detail={errorDetail || "Access to this information is outside your authorized scope."}
        />
      )}

      {/* Error Alert */}
      {errorDetail && !isAccessDenied && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-700 shrink-0 mt-0.5" />
          <span>{errorDetail}</span>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="h-72 flex flex-col items-center justify-center bg-white border border-slate-200 rounded-xl gap-3 shadow-xs">
          <div className="w-8 h-8 border-3 border-blue-900 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm text-slate-700 font-semibold">Analyzing authorized documents...</span>
          <span className="text-xs text-slate-500 font-mono">
            Evaluating keyword frequencies &amp; topic clusters
          </span>
        </div>
      )}

      {/* Main Results Display */}
      {topicData && !loading && (
        <div className="space-y-6">
          {/* Top Section: Word Cloud & Key Terminology Table */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Visual Terminology Word Cloud */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col items-center justify-between">
              <div className="w-full flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <CloudSun className="w-5 h-5 text-blue-900" />
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">Visual Terminology Cloud</h2>
                </div>
                {topicData.wordcloud_url && (
                  <a
                    href={
                      topicData.wordcloud_url.startsWith("http")
                        ? topicData.wordcloud_url
                        : `${getApiBase()}${topicData.wordcloud_url}`
                    }
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-blue-900 font-bold hover:underline flex items-center gap-1.5 cursor-pointer"
                  >
                    <Download className="w-4 h-4" /> Download Image
                  </a>
                )}
              </div>

              {topicData.wordcloud_url ? (
                <div className="w-full bg-slate-50 rounded-lg p-3 border border-slate-200 flex flex-col items-center justify-center overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={
                      topicData.wordcloud_url.startsWith("http")
                        ? topicData.wordcloud_url
                        : `${getApiBase()}${topicData.wordcloud_url}`
                    }
                    alt="Authorized Topic Word Cloud"
                    className="max-h-64 object-contain rounded"
                  />
                  <div className="w-full flex items-center justify-end text-xs text-slate-500 font-mono pt-2">
                    <span>Colormap: Viridis</span>
                  </div>
                </div>
              ) : (
                <div className="h-60 w-full flex flex-col items-center justify-center text-sm text-slate-500 bg-slate-50 rounded-lg border border-slate-200">
                  <CloudSun className="w-8 h-8 text-slate-400 mb-2" />
                  <p>Word cloud not available for selected scope.</p>
                </div>
              )}
            </div>

            {/* Key Terms Table */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Hash className="w-5 h-5 text-blue-900" />
                  <h2 className="text-base sm:text-lg font-bold text-slate-900">Key Domain Terms (TF-IDF)</h2>
                </div>
                <span className="text-xs sm:text-sm text-slate-600 font-mono font-bold">
                  {topicData.keywords?.length || 0} Terms
                </span>
              </div>

              <div className="overflow-y-auto max-h-64 border border-slate-200 rounded-lg">
                <table className="w-full text-left text-sm border-collapse">
                  <thead className="bg-slate-50 text-slate-800 font-bold sticky top-0 border-b border-slate-200 text-xs uppercase tracking-wider">
                    <tr>
                      <th className="py-2.5 px-3.5 w-12">#</th>
                      <th className="py-2.5 px-3.5">Keyword</th>
                      <th className="py-2.5 px-3.5 text-right">Frequency</th>
                      <th className="py-2.5 px-3.5 text-right">Documents</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-800 font-sans">
                    {!topicData.keywords || topicData.keywords.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="py-6 text-center text-slate-500 text-sm">
                          No key terms extracted for the selected criteria.
                        </td>
                      </tr>
                    ) : (
                      topicData.keywords.map((k, idx) => {
                        const rank = k.rank ?? idx + 1;
                        const freq = Number(k.frequency ?? 0);
                        const docs = Number(k.document_count ?? 0);

                        return (
                          <tr key={rank || idx} className="hover:bg-slate-50 transition-colors">
                            <td className="py-2.5 px-3.5 text-slate-500 font-mono text-xs font-bold">{rank}</td>
                            <td className="py-2.5 px-3.5 font-bold text-slate-900">{k.keyword}</td>
                            <td className="py-2.5 px-3.5 font-mono text-slate-700 text-right font-semibold">{freq}</td>
                            <td className="py-2.5 px-3.5 font-mono text-slate-600 text-right">{docs}</td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Identified Topics Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg sm:text-xl font-black text-slate-900 flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-900" />
                Thematic Topic Clusters ({(topicData.topics || []).length})
              </h2>
            </div>

            {!topicData.topics || topicData.topics.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500 border border-slate-200 rounded-xl bg-white shadow-xs">
                No topic clusters identified in the selected authorized corpus.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {topicData.topics.map((t, tIdx) => {
                  const chunkCount = Number(t.chunk_count ?? t.document_chunk_count ?? 0);
                  const safeChunkCount = Number.isFinite(chunkCount) && chunkCount >= 0 ? chunkCount : 0;
                  const rawPct = Number(t.percentage_of_corpus ?? 0);
                  const displayPercentage = Number.isFinite(rawPct) ? rawPct.toFixed(1) : "0.0";
                  const topKeywords = Array.isArray(t.top_keywords) ? t.top_keywords : [];
                  const excerpts = Array.isArray(t.representative_excerpts)
                    ? t.representative_excerpts
                    : Array.isArray(t.representative_quotes)
                    ? t.representative_quotes
                    : [];
                  const minesCovered = Array.isArray(t.mines_covered) ? t.mines_covered : [];

                  return (
                    <div
                      key={t.topic_id || `topic-${tIdx}`}
                      className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs space-y-3 hover:border-slate-300 transition"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-xs font-mono font-bold text-blue-900 uppercase tracking-wider block">
                            {t.topic_id || `TOPIC-${tIdx + 1}`}
                          </span>
                          <h3 className="font-bold text-base sm:text-lg text-slate-900 mt-0.5">
                            {t.title || `Topic ${tIdx + 1}`}
                          </h3>
                        </div>
                        <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 text-slate-800 font-mono shrink-0">
                          {safeChunkCount} sections ({displayPercentage}%)
                        </span>
                      </div>

                      <p className="text-sm text-slate-700 leading-relaxed">
                        {t.description || "Thematic cluster identified across authorized reports."}
                      </p>

                      {/* Mines Covered Tag */}
                      {minesCovered.length > 0 && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium">
                          <Building className="w-3.5 h-3.5 text-slate-400" />
                          <span>Mines:</span>
                          <div className="flex flex-wrap gap-1.5">
                            {minesCovered.map((m, mIdx) => (
                              <span
                                key={mIdx}
                                className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-xs font-semibold"
                              >
                                {m}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Keywords Badges */}
                      {topKeywords.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {topKeywords.map((kw, idx) => (
                            <span
                              key={idx}
                              className="px-2.5 py-1 rounded-md text-xs bg-slate-50 text-slate-800 font-semibold border border-slate-200"
                            >
                              #{kw}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Representative Excerpt without quotes or synthetic badges */}
                      {excerpts.length > 0 && (
                        <div className="pt-2.5 border-t border-slate-100 space-y-1">
                          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                            Domain Observation Reference
                          </span>
                          <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                            {excerpts[0].replace(/^["'“”]|["'“”]$/g, "")}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
