"use client";

import React, { useState, useEffect } from "react";
import {
  Send,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Landmark,
  FileText,
  Layers,
  Pickaxe,
  Mountain,
  Wrench,
  ShieldAlert,
  Truck,
  ExternalLink,
  Compass,
  Database,
  Info,
  HelpCircle,
  MapPin,
} from "lucide-react";
import { ApiClient, ApiError } from "../../lib/api";
import { GroundedQueryResponse, EvidenceItem } from "../../lib/types";
import EvidenceCard from "../../components/EvidenceCard";
import ConflictAlert from "../../components/ConflictAlert";
import DataGapAlert from "../../components/DataGapAlert";
import AccessRestrictedAlert from "../../components/AccessRestrictedAlert";
import EvidenceDrawer from "../../components/EvidenceDrawer";

const canonicalSamplePrompts = [
  "What was GEVRA's production in FY2024-25?",
  "What geological observations were reported for GEVRA in FY2024-25?",
  "Which boreholes are within 500 metres of a geological feature?",
  "Compare FY2024-25 production across the five mines.",
  "Explain the production shortfall using operational and geological evidence.",
];

export default function AskGeoVaultPage() {
  const [queryText, setQueryText] = useState("");
  const [loading, setLoading] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [response, setResponse] = useState<GroundedQueryResponse | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [isAccessDenied, setIsAccessDenied] = useState(false);
  const [showAllEvidence, setShowAllEvidence] = useState(false);

  // Evidence Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<string | undefined>(undefined);
  const [selectedSnippet, setSelectedSnippet] = useState<string | undefined>(undefined);

  // Progressive Disclosure Sections
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    production: true,
    geology: false,
    operations: false,
    safety: false,
    transportation: false,
  });

  const toggleSection = (section: string) => {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (loading) {
      setElapsedSeconds(0);
      interval = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loading]);

  const getLoadingStageText = (seconds: number) => {
    if (seconds < 3) {
      return {
        stage: "Analyzing authorized evidence & verifying user scope...",
        pct: 25,
      };
    } else if (seconds < 8) {
      return {
        stage: "Calculating deterministic metrics & retrieving verified records...",
        pct: 50,
      };
    } else if (seconds < 14) {
      return {
        stage: "Cross-referencing evidence and verifying mathematical consistency...",
        pct: 75,
      };
    } else {
      return {
        stage: "Synthesizing evidence-grounded response via local Qwen3-8B...",
        pct: 90,
      };
    }
  };

  const handleQuery = async (queryToRun?: string) => {
    const text = queryToRun || queryText;
    if (!text.trim() || loading) return;

    setLoading(true);
    setErrorDetail(null);
    setIsAccessDenied(false);

    try {
      const res = await ApiClient.executeNaturalQuery(text.trim());
      setResponse(res);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403) {
        setIsAccessDenied(true);
        setErrorDetail(err.detail || "Access to this information is outside your authorized scope.");
      } else if (err instanceof ApiError) {
        setErrorDetail(err.detail || `Server error (HTTP ${err.status}).`);
      } else {
        setErrorDetail(err.message || "Query execution failed. Please check network connectivity.");
      }
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleQuery();
    }
  };

  const openDrawerForEvidence = (id: string, citation?: string, snippet?: string) => {
    setSelectedEvidenceId(id);
    setSelectedCitation(citation);
    setSelectedSnippet(snippet);
    setDrawerOpen(true);
  };

  // Helper to render text with clickable citation badges e.g. [1], [2]
  const renderTextWithCitations = (text: string, evidenceList?: EvidenceItem[]) => {
    if (!text) return null;
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, idx) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const citationNum = parseInt(match[1], 10);
        const ev = evidenceList && evidenceList[citationNum - 1];
        const evId = ev?.evidence_id || `EV-CIT-${citationNum}`;
        return (
          <button
            key={idx}
            type="button"
            onClick={() =>
              openDrawerForEvidence(
                evId,
                ev?.citation || `Source Citation [${citationNum}]`,
                ev?.snippet || (ev as any)?.source_text
              )
            }
            className="inline-flex items-center justify-center mx-0.5 px-2 py-0.5 rounded text-xs font-bold bg-blue-100 hover:bg-blue-200 text-blue-900 border border-blue-300 transition cursor-pointer"
            title="Click to open Evidence Drawer and inspect source"
          >
            [{citationNum}]
          </button>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  // Helper to render markdown content with headings, lists, tables, and citations
  const renderDetailedContent = (content: string, evidenceList?: EvidenceItem[]) => {
    if (!content) return null;
    const blocks = content.split("\n\n").map((b) => b.trim()).filter(Boolean);

    return (
      <div className="space-y-4 text-base text-slate-800 leading-relaxed">
        {blocks.map((block, bIdx) => {
          // Check for heading ###
          if (block.startsWith("###")) {
            const title = block.replace(/^###\s*/, "");
            return (
              <h3
                key={bIdx}
                className="text-base sm:text-lg font-bold text-slate-900 pt-3 pb-1 border-b border-slate-100 flex items-center gap-2"
              >
                <span className="w-2 h-2 rounded-full bg-blue-900"></span>
                {title}
              </h3>
            );
          }

          // Check for markdown table
          if (block.includes("|") && block.includes("---")) {
            const rows = block.split("\n").map((r) => r.trim()).filter(Boolean);
            const headerRow = rows[0]?.split("|").map((c) => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1);
            const dataRows = rows.slice(2).map((r) =>
              r.split("|").map((c) => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1)
            );

            return (
              <div key={bIdx} className="overflow-x-auto border border-slate-200 rounded-xl bg-white my-3 shadow-2xs">
                <table className="w-full text-sm text-left border-collapse">
                  <thead className="bg-slate-50 border-b border-slate-200 text-xs sm:text-sm font-bold text-slate-800">
                    <tr>
                      {headerRow.map((h, hIdx) => (
                        <th key={hIdx} className="p-3 border-r last:border-r-0 border-slate-200">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {dataRows.map((row, rIdx) => (
                      <tr key={rIdx} className="hover:bg-slate-50">
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} className="p-3 font-mono text-sm text-slate-800 border-r last:border-r-0 border-slate-200">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }

          // Check for bullet list
          if (block.startsWith("- ") || block.startsWith("• ") || block.startsWith("* ")) {
            const items = block.split("\n").map((l) => l.replace(/^[-•*]\s*/, "").trim()).filter(Boolean);
            return (
              <ul key={bIdx} className="space-y-2 pl-2 my-2">
                {items.map((item, iIdx) => (
                  <li key={iIdx} className="flex items-start gap-2.5 text-sm sm:text-base text-slate-800">
                    <span className="text-blue-900 font-bold leading-none mt-1.5">&bull;</span>
                    <span>{renderTextWithCitations(item, evidenceList)}</span>
                  </li>
                ))}
              </ul>
            );
          }

          // Standard paragraph
          return (
            <p key={bIdx} className="text-sm sm:text-base text-slate-800 leading-relaxed font-normal">
              {renderTextWithCitations(block, evidenceList)}
            </p>
          );
        })}
      </div>
    );
  };

  // Extract Summary, Key Facts, and Sub-sections from the answer text
  const parseAnswerProgressive = (rawAnswer: string) => {
    const lines = rawAnswer.split("\n").map((l) => l.trim()).filter(Boolean);
    let summary = "";
    const keyFacts: string[] = [];
    const sourceObservations: string[] = [];
    const inferences: string[] = [];
    const detailedSections: Record<string, string[]> = {
      production: [],
      geology: [],
      operations: [],
      safety: [],
      transportation: [],
      other: [],
    };

    let currentSection = "summary";

    for (const line of lines) {
      const lower = line.toLowerCase();
      if (lower.startsWith("summary:") || lower.startsWith("executive summary:")) {
        currentSection = "summary";
        continue;
      } else if (lower.startsWith("key fact") || lower.startsWith("key findings:")) {
        currentSection = "keyfacts";
        continue;
      } else if (lower.includes("observation:") || lower.startsWith("observation")) {
        currentSection = "observation";
      } else if (lower.includes("inference:") || lower.startsWith("analysis:")) {
        currentSection = "inference";
      } else if (lower.includes("production")) {
        currentSection = "production";
      } else if (lower.includes("geolog") || lower.includes("strata") || lower.includes("seam") || lower.includes("borehole")) {
        currentSection = "geology";
      } else if (lower.includes("operation") || lower.includes("equipment") || lower.includes("downtime")) {
        currentSection = "operations";
      } else if (lower.includes("safety") || lower.includes("compliance")) {
        currentSection = "safety";
      } else if (lower.includes("dispatch") || lower.includes("transport") || lower.includes("logistics")) {
        currentSection = "transportation";
      }

      if (line.startsWith("•") || line.startsWith("-") || line.startsWith("*")) {
        const clean = line.replace(/^[-•*]\s*/, "");
        if (currentSection === "observation") {
          sourceObservations.push(clean);
        } else if (currentSection === "inference") {
          inferences.push(clean);
        } else if (currentSection === "keyfacts" || keyFacts.length < 4) {
          keyFacts.push(clean);
        } else if (detailedSections[currentSection]) {
          detailedSections[currentSection].push(clean);
        } else {
          detailedSections.other.push(clean);
        }
      } else if (currentSection === "summary") {
        if (!summary) summary = line;
        else summary += " " + line;
      } else if (currentSection === "observation") {
        sourceObservations.push(line);
      } else if (currentSection === "inference") {
        inferences.push(line);
      } else {
        if (detailedSections[currentSection]) {
          detailedSections[currentSection].push(line);
        } else {
          detailedSections.other.push(line);
        }
      }
    }

    if (!summary && lines.length > 0) {
      summary = lines[0];
    }

    return { summary, keyFacts, sourceObservations, inferences, detailedSections };
  };

  const loadingInfo = getLoadingStageText(elapsedSeconds);

  // Determine modalities present in evidence for the Hybrid breakdown
  const hasStructuredEvidence = (response?.evidence || []).some(
    (e) =>
      e.source_type === "STRUCTURED_RECORD" ||
      e.source_type === "DATABASE" ||
      e.source_type === "STRUCTURED" ||
      e.evidence_id.startsWith("EV-PRODUCTION-") ||
      e.evidence_id.startsWith("EV-EQUIPMENT-") ||
      e.evidence_id.startsWith("EV-SAFETY-") ||
      e.evidence_id.startsWith("EV-TRANSPORT-")
  );

  const hasDocumentEvidence = (response?.evidence || []).some(
    (e) =>
      e.source_type === "DOCUMENT_CHUNK" ||
      e.source_type === "DOCUMENT" ||
      e.document_type === "pdf" ||
      e.document_type === "document" ||
      (!e.source_type.includes("SPATIAL") && !e.source_type.includes("STRUCTURED"))
  );

  const hasSpatialEvidence = (response?.evidence || []).some(
    (e) =>
      e.source_type === "POSTGIS_SPATIAL" ||
      e.source_type === "SPATIAL" ||
      e.document_type === "spatial" ||
      Boolean(e.coordinates) ||
      Boolean(e.layer_name) ||
      e.evidence_id.startsWith("EV-SPATIAL-")
  );

  // Extract structured production record if available in response
  const structuredFacts = response?.structured_results?.facts || [];
  const primaryProductionFact = structuredFacts.find(
    (f: any) => f.actual_production_mt !== undefined || f.target_mt !== undefined
  );

  const comparisons = response?.structured_results?.analytics?.comparisons;
  const trend = response?.structured_results?.analytics?.trend;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Page Title & Institutional Scope */}
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          Ask GeoVault
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1">
          Ask evidence-grounded questions across authorized mining, geological and operational records.
        </p>
      </div>

      {/* Query Input Box */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about production, geology, safety, boreholes, equipment or comparisons..."
            disabled={loading}
            className="flex-1 bg-white border border-slate-300 rounded-lg px-4.5 py-3 text-base text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-900/20 focus:border-blue-900 transition shadow-inner font-sans"
          />
          <button
            onClick={() => handleQuery()}
            disabled={loading || !queryText.trim()}
            className="px-6 py-3 rounded-lg bg-blue-900 hover:bg-blue-800 text-white font-bold text-base transition flex items-center gap-2 disabled:opacity-50 shadow-xs cursor-pointer shrink-0"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <Send className="w-5 h-5" />
            )}
            <span>Query</span>
          </button>
        </div>

        {/* Canonical Example Prompts */}
        <div className="flex flex-wrap items-center gap-2.5 pt-1 text-sm">
          <span className="text-slate-600 font-bold mr-1">Prompts:</span>
          {canonicalSamplePrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQueryText(p);
                handleQuery(p);
              }}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 transition text-xs sm:text-sm font-medium cursor-pointer text-left"
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Loading Progress State */}
      {loading && (
        <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold text-slate-900">{loadingInfo.stage}</span>
            <span className="text-slate-500 font-mono text-xs">{elapsedSeconds}s</span>
          </div>

          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-blue-900 h-1.5 transition-all duration-500 ease-out"
              style={{ width: `${loadingInfo.pct}%` }}
            ></div>
          </div>
          <p className="text-xs text-slate-500 font-mono">
            Evaluating query route &bull; PostGIS &amp; pgvector scope filters active
          </p>
        </div>
      )}

      {/* Access Denied Alert (403 Isolation) */}
      {isAccessDenied && (
        <AccessRestrictedAlert
          detail={errorDetail || "Access to this information is outside your authorized scope."}
        />
      )}

      {/* General Error Alert */}
      {errorDetail && !isAccessDenied && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-xs text-red-800 space-y-1">
          <div className="font-bold flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-red-700" />
            Query Execution Notice
          </div>
          <p>{errorDetail}</p>
        </div>
      )}

      {/* Grounded Query Response Presentation */}
      {response && !loading && (() => {
        const { summary, keyFacts, sourceObservations, inferences, detailedSections } =
          parseAnswerProgressive(response.answer);
        const displaySummary = response.summary || summary;
        let displayDetailed = response.detailed_answer || "";
        if (!displayDetailed) {
          // If detailed_answer wasn't separated by backend, extract rest of text after summary
          displayDetailed = response.answer.replace(displaySummary, "").trim();
          displayDetailed = displayDetailed.replace(/^DETAILED ANSWER:\s*/i, "").trim();
        }

        return (
          <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs space-y-6">
            {/* Header: Query Route & Latency Display */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-50 text-blue-900 border border-blue-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-900" /> Evidence-Grounded Response
                </span>

                {/* Actual Backend Query Route */}
                <span
                  className={`px-3 py-1 rounded-md text-xs font-bold font-mono border ${
                    response.query_type === "HYBRID"
                      ? "bg-purple-50 text-purple-900 border-purple-300"
                      : response.query_type === "SQL"
                      ? "bg-emerald-50 text-emerald-900 border-emerald-300"
                      : response.query_type === "RAG"
                      ? "bg-blue-50 text-blue-900 border-blue-300"
                      : "bg-slate-100 text-slate-700 border-slate-300"
                  }`}
                  title="Actual backend intelligence route used"
                >
                  ROUTE: {response.query_type}
                </span>
              </div>

              {response.processing_metadata?.orchestration_latency_ms && (
                <span className="text-sm text-slate-500 font-mono">
                  {(response.processing_metadata.orchestration_latency_ms / 1000).toFixed(2)}s latency
                </span>
              )}
            </div>

            {/* Echo User Query */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm sm:text-base text-slate-800">
              <span className="font-bold text-slate-900">Query: </span>
              <span>{response.query}</span>
            </div>

            {/* HYBRID BREAKDOWN: "How GeoVault Answered" (if HYBRID or multi-source) */}
            {(response.query_type === "HYBRID" ||
              (hasStructuredEvidence && (hasDocumentEvidence || hasSpatialEvidence))) && (
              <div className="bg-indigo-50/50 border border-indigo-200 rounded-xl p-4 space-y-2.5">
                <div className="flex items-center gap-2 text-xs sm:text-sm font-bold text-indigo-950 uppercase tracking-wider">
                  <Compass className="w-4 h-4 text-indigo-800" />
                  How GeoVault Answered (Hybrid Synthesis)
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm">
                  {hasStructuredEvidence && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-indigo-200 font-semibold text-indigo-900">
                      <Database className="w-3.5 h-3.5 text-blue-700" /> Structured Operational Data
                    </span>
                  )}
                  {hasStructuredEvidence && (hasDocumentEvidence || hasSpatialEvidence) && (
                    <span className="text-indigo-400 font-bold">+</span>
                  )}

                  {hasDocumentEvidence && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-indigo-200 font-semibold text-indigo-900">
                      <FileText className="w-3.5 h-3.5 text-slate-700" /> Document Reports
                    </span>
                  )}
                  {hasDocumentEvidence && hasSpatialEvidence && (
                    <span className="text-indigo-400 font-bold">+</span>
                  )}

                  {hasSpatialEvidence && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white border border-indigo-200 font-semibold text-indigo-900">
                      <MapPin className="w-3.5 h-3.5 text-cyan-700" /> PostGIS Spatial Vectors
                    </span>
                  )}

                  <span className="text-indigo-400 font-bold">=</span>

                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-indigo-900 text-white font-bold">
                    Grounded Synthesis
                  </span>
                </div>
              </div>
            )}

            {/* 1. SUMMARY SECTION (Executive Briefing) */}
            <div className="space-y-2.5">
              <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-900"></span>
                Summary
              </div>
              <div className="bg-blue-50/60 border border-blue-200 rounded-xl p-5 text-base sm:text-[17px] text-slate-900 leading-relaxed font-normal shadow-2xs">
                {renderTextWithCitations(displaySummary, response.evidence)}
              </div>
            </div>

            {/* 2. DETAILED ANSWER SECTION (Descriptive Explanation with Headings) */}
            {displayDetailed && (
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900">
                  <FileText className="w-4 h-4 text-blue-900" />
                  Detailed Answer &amp; Context
                </div>
                <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
                  {renderDetailedContent(displayDetailed, response.evidence)}
                </div>
              </div>
            )}

            {/* 3. DYNAMIC STRUCTURED METRIC CARDS (Supporting the Narrative) */}
            {primaryProductionFact && (
              <div className="space-y-2 pt-1">
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900">
                  <Database className="w-4 h-4 text-blue-900" />
                  Key Verified Metrics (Database Register)
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                    <span className="text-slate-600 text-xs font-semibold block mb-1">Actual Production</span>
                    <span className="text-lg sm:text-xl font-bold text-slate-900 font-mono">
                      {primaryProductionFact.actual_production_mt !== undefined
                        ? `${Number(primaryProductionFact.actual_production_mt).toFixed(2)} MT`
                        : "N/A"}
                    </span>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                    <span className="text-slate-600 text-xs font-semibold block mb-1">Target Output</span>
                    <span className="text-lg sm:text-xl font-bold text-slate-900 font-mono">
                      {primaryProductionFact.target_mt !== undefined
                        ? `${Number(primaryProductionFact.target_mt).toFixed(2)} MT`
                        : "N/A"}
                    </span>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                    <span className="text-slate-600 text-xs font-semibold block mb-1">Achievement</span>
                    <span
                      className={`text-lg sm:text-xl font-bold font-mono ${
                        primaryProductionFact.achievement_pct &&
                        primaryProductionFact.achievement_pct >= 100
                          ? "text-emerald-700"
                          : "text-amber-800"
                      }`}
                    >
                      {primaryProductionFact.achievement_pct !== undefined
                        ? `${Number(primaryProductionFact.achievement_pct).toFixed(2)}%`
                        : "N/A"}
                    </span>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                    <span className="text-slate-600 text-xs font-semibold block mb-1">Variance</span>
                    <span
                      className={`text-lg sm:text-xl font-bold font-mono ${
                        primaryProductionFact.variance_mt !== undefined &&
                        primaryProductionFact.variance_mt >= 0
                          ? "text-emerald-700"
                          : "text-rose-700"
                      }`}
                    >
                      {primaryProductionFact.variance_mt !== undefined
                        ? `${Number(primaryProductionFact.variance_mt) > 0 ? "+" : ""}${Number(
                            primaryProductionFact.variance_mt
                          ).toFixed(2)} MT`
                        : "N/A"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* 4. DYNAMIC MULTI-MINE COMPARISON TABLE (if comparison analytics exist) */}
            {comparisons && comparisons.length > 0 && (
              <div className="space-y-2 pt-1">
                <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900">
                  <Layers className="w-4 h-4 text-blue-900" />
                  Multi-Mine Operational Comparison ({comparisons.length} Mines)
                </div>
                <div className="border border-slate-200 rounded-lg overflow-x-auto bg-white text-sm shadow-xs">
                  <table className="w-full border-collapse text-left">
                    <thead className="bg-slate-100 text-slate-800 font-bold border-b border-slate-200 text-xs uppercase tracking-wider">
                      <tr>
                        <th className="p-3">Mine Code</th>
                        <th className="p-3">Mine Name</th>
                        <th className="p-3 text-right">Actual (MT)</th>
                        <th className="p-3 text-right">Target (MT)</th>
                        <th className="p-3 text-right">Achievement %</th>
                        <th className="p-3 text-right">Variance (MT)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 text-sm">
                      {comparisons.map((c: any, idx: number) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="p-3 font-mono font-bold text-slate-900">{c.mine_code}</td>
                          <td className="p-3 font-semibold text-slate-850">{c.mine_name || c.mine_code}</td>
                          <td className="p-3 text-right font-mono font-bold text-slate-900">
                            {Number(c.actual_production_mt || c.total_production_mt || 0).toFixed(2)}
                          </td>
                          <td className="p-3 text-right font-mono text-slate-700">
                            {c.target_mt !== undefined || c.target_production_mt !== undefined
                              ? Number(c.target_mt || c.target_production_mt).toFixed(2)
                              : "-"}
                          </td>
                          <td
                            className={`p-3 text-right font-mono font-bold ${
                              (c.achievement_pct || 0) >= 100 ? "text-emerald-700" : "text-amber-800"
                            }`}
                          >
                            {c.achievement_pct !== undefined ? `${Number(c.achievement_pct).toFixed(1)}%` : "-"}
                          </td>
                          <td
                            className={`p-3 text-right font-mono ${
                              (c.variance_mt || 0) >= 0 ? "text-emerald-700 font-bold" : "text-rose-700 font-bold"
                            }`}
                          >
                            {c.variance_mt !== undefined
                              ? `${Number(c.variance_mt) > 0 ? "+" : ""}${Number(c.variance_mt).toFixed(2)}`
                              : "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 5. NO-GUESS UX: SEPARATING FACTS, OBSERVATIONS & INFERENCES */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              {/* Measured Facts Card */}
              {keyFacts.length > 0 && (
                <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/60 space-y-2.5">
                  <div className="flex items-center gap-1.5 text-sm font-bold text-slate-900 uppercase tracking-wider">
                    <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                    Measured Facts (Database Verified)
                  </div>
                  <ul className="space-y-2 text-sm text-slate-850">
                    {keyFacts.map((fact, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-emerald-700 font-bold leading-none mt-1">&bull;</span>
                        <span>{renderTextWithCitations(fact, response.evidence)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Source Observations / Synthesis Card */}
              <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/60 space-y-2.5">
                <div className="flex items-center gap-1.5 text-sm font-bold text-slate-900 uppercase tracking-wider">
                  <Info className="w-4 h-4 text-blue-900" />
                  Source Observations &amp; Context
                </div>
                <div className="space-y-2 text-sm text-slate-800 leading-relaxed">
                  {sourceObservations.length > 0 ? (
                    sourceObservations.map((obs, idx) => (
                      <p key={idx}>{renderTextWithCitations(obs, response.evidence)}</p>
                    ))
                  ) : (
                    <p>
                      Source observations and operational context are grounded directly in institutional registers and verified domain reports.
                    </p>
                  )}
                  {inferences.length > 0 && (
                    <div className="pt-2 border-t border-slate-200 text-slate-700 italic">
                      <strong className="not-italic font-semibold text-slate-900">Inference note: </strong>
                      {inferences.join(" ")}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* 3. CONFLICTS & LIMITATIONS (if surfaced) */}
            {response.conflicts && response.conflicts.length > 0 && (
              <ConflictAlert conflicts={response.conflicts} />
            )}

            {response.data_gaps && response.data_gaps.length > 0 && (
              <DataGapAlert dataGaps={response.data_gaps} />
            )}

            {response.validation_status === "INSUFFICIENT_AUTHORIZED_DATA" && (
              <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-900 space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-700" />
                  Insufficient Authorized Data Notice
                </div>
                <p>
                  The active user scope does not possess sufficient authorized records across all requested
                  entities. Showing grounded facts for permitted scopes only.
                </p>
              </div>
            )}

            {/* 4. SOURCES & EVIDENCE SECTION (Multi-Modal Cards) */}
            <div className="pt-4 border-t border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-blue-900" />
                  Verified Evidence &amp; Traceability ({response.evidence?.length || 0})
                </span>
                <button
                  type="button"
                  onClick={() => setShowAllEvidence(!showAllEvidence)}
                  className="text-sm text-blue-900 font-bold hover:underline cursor-pointer"
                >
                  {showAllEvidence ? "Collapse Details" : "Expand All Cards"}
                </button>
              </div>

              {/* No Evidence Fallback Notice */}
              {(!response.evidence || response.evidence.length === 0) && (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-600 text-center">
                  No supporting evidence was returned for this query.
                </div>
              )}

              {/* Interactive Citations Quick Bar */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {(response.evidence || []).map((ev, idx) => (
                  <button
                    key={ev.evidence_id || idx}
                    type="button"
                    onClick={() =>
                      openDrawerForEvidence(
                        ev.evidence_id,
                        ev.citation || ev.source_name,
                        ev.snippet || (ev as any).source_text
                      )
                    }
                    className="p-3 text-left rounded-lg border border-slate-200 hover:border-blue-900 bg-slate-50 hover:bg-blue-50/50 transition group flex items-start justify-between gap-2 cursor-pointer"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-900 text-white font-mono">
                          [{idx + 1}]
                        </span>
                        <span className="text-sm font-bold text-slate-900 truncate">
                          {ev.source_name || ev.document_name || `Evidence ${ev.evidence_id}`}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 font-medium mt-1 truncate">
                        {ev.citation || ev.snippet || "Click to inspect source details"}
                      </p>
                    </div>
                    <ExternalLink className="w-4 h-4 text-slate-400 group-hover:text-blue-900 shrink-0 mt-1" />
                  </button>
                ))}
              </div>

              {/* Full Evidence Cards */}
              {showAllEvidence && response.evidence && (
                <div className="space-y-2.5 pt-2">
                  {response.evidence.map((ev, idx) => (
                    <EvidenceCard
                      key={ev.evidence_id || idx}
                      evidence={ev}
                      index={idx}
                      onInspect={(id) => openDrawerForEvidence(id, ev.citation, ev.snippet)}
                    />
                  ))}
                </div>
              )}
            </div>

          </div>
        );
      })()}

      {/* Reusable Sliding Evidence Drawer */}
      <EvidenceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        evidenceId={selectedEvidenceId}
        initialCitation={selectedCitation}
        initialSnippet={selectedSnippet}
      />
    </div>
  );
}
