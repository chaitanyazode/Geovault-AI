"use client";

import React from "react";
import { AlertTriangle, ShieldAlert, UserCheck } from "lucide-react";
import { ConflictItem } from "../lib/types";

interface ConflictAlertProps {
  conflicts: ConflictItem[];
}

export default function ConflictAlert({ conflicts }: ConflictAlertProps) {
  if (!conflicts || conflicts.length === 0) return null;

  return (
    <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 my-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-rose-900 font-bold text-sm sm:text-base">
          <ShieldAlert className="w-5 h-5 text-rose-700 shrink-0" />
          <span>Data Discrepancy Detected — Engineering Verification Required</span>
        </div>
        <span className="text-xs px-2.5 py-1 rounded bg-rose-100 border border-rose-200 text-rose-900 font-mono font-bold">
          {conflicts.length} Conflict{conflicts.length > 1 ? "s" : ""}
        </span>
      </div>

      <div className="space-y-3">
        {conflicts.map((c, i) => (
          <div
            key={c.conflict_id || i}
            className="bg-white border border-rose-200 rounded-lg p-4 text-sm shadow-xs"
          >
            {/* Conflict ID & Topic */}
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-rose-100">
              <span className="font-mono font-bold text-rose-900">{c.conflict_id}</span>
              {c.mine_code && (
                <span className="px-2.5 py-0.5 rounded bg-slate-100 text-xs text-slate-800 font-semibold">
                  Mine: {c.mine_code}
                </span>
              )}
            </div>

            <div className="text-slate-900 font-bold mb-3 text-sm">
              {c.metric_or_topic}
            </div>

            {/* Comparison Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm mb-3">
              {/* Source A */}
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                  Source A ({c.source_a_type})
                </div>
                <div className="font-mono font-bold text-slate-900 text-base">
                  {c.source_a_value}
                </div>
                {c.source_a_reference && (
                  <div className="text-xs text-slate-600 truncate mt-1">
                    Ref: {c.source_a_reference}
                  </div>
                )}
              </div>

              {/* Source B */}
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-slate-500 text-xs uppercase tracking-wider font-bold mb-1">
                  Source B ({c.source_b_type})
                </div>
                <div className="font-mono font-bold text-rose-700 text-base">
                  {c.source_b_value}
                </div>
                {c.source_b_reference && (
                  <div className="text-xs text-slate-600 truncate mt-1">
                    Ref: {c.source_b_reference}
                  </div>
                )}
              </div>
            </div>

            {/* Statutory Human Review Banner */}
            <div className="flex items-start gap-2 pt-2.5 border-t border-slate-100 text-xs sm:text-sm text-slate-800 font-medium">
              <UserCheck className="w-4 h-4 text-slate-600 shrink-0 mt-0.5" />
              <span>
                <strong>Resolution Policy:</strong> {c.resolution_policy || "Independent engineering review required before operational decision-making."}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
