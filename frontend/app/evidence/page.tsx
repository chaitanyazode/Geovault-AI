"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldAlert,
  Search,
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
} from "lucide-react";
import { ApiClient, ApiError } from "../../lib/api";
import { ConflictItem, EvidenceItem, UserProfileResponse } from "../../lib/types";
import ConflictAlert from "../../components/ConflictAlert";
import EvidenceCard from "../../components/EvidenceCard";
import AccessRestrictedAlert from "../../components/AccessRestrictedAlert";

export default function EvidenceConflictsPage() {
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [evidenceIdInput, setEvidenceIdInput] = useState<string>("");
  const [lookedUpEvidence, setLookedUpEvidence] = useState<EvidenceItem | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [isLookupDenied, setIsLookupDenied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [prof, confs] = await Promise.all([
          ApiClient.getUserProfile(),
          ApiClient.getConflicts(),
        ]);
        setProfile(prof);
        setConflicts(confs);
      } catch (err) {
        console.error("Failed to load conflicts:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleLookupEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!evidenceIdInput.trim() || lookupLoading) return;

    setLookupLoading(true);
    setLookupError(null);
    setIsLookupDenied(false);
    setLookedUpEvidence(null);

    try {
      const ev = await ApiClient.getEvidenceItem(evidenceIdInput.trim());
      setLookedUpEvidence(ev);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403) {
        setIsLookupDenied(true);
        setLookupError(err.detail);
      } else {
        setLookupError(err.detail || err.message || "Evidence record not found.");
      }
    } finally {
      setLookupLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Title Header */}
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          Evidence &amp; Discrepancies
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1">
          Review verified source citations, document page references, and registered data discrepancies.
        </p>
      </div>

      {/* 1. Conflicts Section */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            Registered Discrepancies ({conflicts.length})
          </h2>
          <span className="text-xs sm:text-sm text-slate-500 font-medium">
            Filtered by authorized mine scope
          </span>
        </div>

        {conflicts.length > 0 ? (
          <ConflictAlert conflicts={conflicts} />
        ) : (
          <div className="p-5 rounded-xl bg-white border border-slate-200 text-sm text-slate-700 flex items-center gap-3 shadow-xs">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>Zero unresolved data discrepancies recorded for your active authorized scope.</span>
          </div>
        )}
      </section>

      {/* 2. Evidence Citation Lookup Section */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-blue-900" />
            Evidence Record Lookup
          </h2>
          <p className="text-sm text-slate-600 mt-1">
            Enter an Evidence ID to inspect provenance, table record references, and page numbers.
          </p>
        </div>

        <form onSubmit={handleLookupEvidence} className="flex flex-col sm:flex-row gap-2.5 text-sm">
          <input
            type="text"
            value={evidenceIdInput}
            onChange={(e) => setEvidenceIdInput(e.target.value)}
            placeholder="e.g. EV-PRODUCTION-GEVRA-2024 or EV-SPATIAL-GEVRA-GV-BH-001"
            className="flex-1 bg-white border border-slate-300 rounded-lg px-4 py-2.5 text-slate-900 focus:outline-none focus:border-blue-900 font-mono text-sm"
          />
          <button
            type="submit"
            disabled={lookupLoading || !evidenceIdInput.trim()}
            className="px-5 py-2.5 rounded-lg bg-blue-900 hover:bg-blue-800 text-white font-bold text-sm transition disabled:opacity-50 cursor-pointer shadow-xs"
          >
            {lookupLoading ? "Inspecting..." : "Inspect Citation"}
          </button>
        </form>

        {/* Quick Sample Lookup Chips */}
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600 pt-1">
          <span className="font-medium">Sample Citations:</span>
          <button
            onClick={() => {
              setEvidenceIdInput("EV-PRODUCTION-GEVRA-2024");
            }}
            className="px-3 py-1.5 rounded-md bg-slate-50 hover:bg-slate-100 text-slate-800 font-mono text-xs font-semibold border border-slate-200 transition cursor-pointer"
          >
            EV-PRODUCTION-GEVRA-2024
          </button>
          <button
            onClick={() => {
              setEvidenceIdInput("EV-SPATIAL-GEVRA-GV-BH-001");
            }}
            className="px-3 py-1.5 rounded-md bg-slate-50 hover:bg-slate-100 text-slate-800 font-mono text-xs font-semibold border border-slate-200 transition cursor-pointer"
          >
            EV-SPATIAL-GEVRA-GV-BH-001
          </button>
          <button
            onClick={() => {
              setEvidenceIdInput("EV-PRODUCTION-KUSMUNDA-2024");
            }}
            className="px-3 py-1.5 rounded-md bg-slate-50 hover:bg-slate-100 text-slate-800 font-mono text-xs font-semibold border border-slate-200 transition cursor-pointer"
          >
            EV-PRODUCTION-KUSMUNDA-2024
          </button>
        </div>

        {/* Access Denied / Error on Lookup */}
        {isLookupDenied && <AccessRestrictedAlert detail={lookupError || undefined} />}
        {lookupError && !isLookupDenied && (
          <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">
            {lookupError}
          </div>
        )}

        {/* Looked up Evidence Card */}
        {lookedUpEvidence && (
          <div className="pt-2">
            <EvidenceCard evidence={lookedUpEvidence} />
          </div>
        )}
      </section>
    </div>
  );
}
