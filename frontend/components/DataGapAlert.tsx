"use client";

import React from "react";
import { AlertCircle, HelpCircle } from "lucide-react";
import { DataGapItem } from "../lib/types";

interface DataGapAlertProps {
  dataGaps: (DataGapItem | string)[];
}

export default function DataGapAlert({ dataGaps }: DataGapAlertProps) {
  if (!dataGaps || dataGaps.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4.5 my-3 text-sm">
      <div className="flex items-center gap-2 text-amber-900 font-bold mb-2.5 text-sm sm:text-base">
        <AlertCircle className="w-4.5 h-4.5 text-amber-700 shrink-0" />
        <span>Data Gaps Identified in Requested Scope</span>
      </div>

      <div className="space-y-2">
        {dataGaps.map((gap, i) => {
          const desc = typeof gap === "string" ? gap : gap.description;
          const meta = typeof gap === "object" ? `${gap.mine_code || ""} ${gap.year ? `(FY${gap.year})` : ""}` : "";
          return (
            <div
              key={i}
              className="flex items-start gap-2.5 bg-white border border-amber-200 p-3 rounded-lg text-slate-800 text-sm shadow-xs"
            >
              <HelpCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                {meta && <strong className="text-slate-900 mr-1.5">{meta.trim()}:</strong>}
                {desc}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-2.5 text-xs text-slate-600">
        Notice: GeoVault AI adheres strictly to the verified evidence policy. Missing values are flagged as data gaps and never fabricated.
      </div>
    </div>
  );
}
