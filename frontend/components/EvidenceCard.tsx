"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  FileText,
  ChevronDown,
  ChevronUp,
  Hash,
  Building,
  MapPin,
  Database,
  Layers,
  Mountain,
  Compass,
  Calendar,
  ExternalLink,
} from "lucide-react";
import { EvidenceItem } from "../lib/types";

interface EvidenceCardProps {
  evidence: EvidenceItem;
  index?: number;
  onInspect?: (evidenceId: string) => void;
}

export default function EvidenceCard({ evidence, index, onInspect }: EvidenceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Modality detection
  const isSpatial =
    evidence.source_type === "POSTGIS_SPATIAL" ||
    evidence.source_type === "SPATIAL" ||
    evidence.document_type === "spatial" ||
    Boolean(evidence.coordinates) ||
    Boolean(evidence.layer_name) ||
    evidence.evidence_id.startsWith("EV-SPATIAL-");

  const isStructured =
    !isSpatial &&
    (evidence.source_type === "STRUCTURED_RECORD" ||
      evidence.source_type === "DATABASE" ||
      evidence.source_type === "STRUCTURED" ||
      evidence.evidence_id.startsWith("EV-PRODUCTION-") ||
      evidence.evidence_id.startsWith("EV-EQUIPMENT-") ||
      evidence.evidence_id.startsWith("EV-SAFETY-") ||
      evidence.evidence_id.startsWith("EV-TRANSPORT-") ||
      evidence.evidence_id.startsWith("EV-SEAM-") ||
      evidence.evidence_id.startsWith("EV-ZONE-") ||
      evidence.evidence_id.startsWith("EV-BOREHOLE-"));

  const isGeology =
    evidence.department === "Geology" ||
    evidence.evidence_id.startsWith("EV-SEAM-") ||
    evidence.evidence_id.startsWith("EV-ZONE-") ||
    evidence.evidence_id.startsWith("EV-BOREHOLE-") ||
    (evidence.source_name && evidence.source_name.toLowerCase().includes("geolog"));

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 text-sm transition hover:border-slate-300 shadow-xs space-y-3">
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
              isSpatial
                ? "bg-cyan-50 text-cyan-800 border-cyan-200"
                : isGeology
                ? "bg-purple-50 text-purple-800 border-purple-200"
                : isStructured
                ? "bg-blue-50 text-blue-900 border-blue-200"
                : "bg-slate-50 text-slate-700 border-slate-200"
            }`}
          >
            {isSpatial ? (
              <MapPin className="w-4 h-4" />
            ) : isGeology ? (
              <Mountain className="w-4 h-4" />
            ) : isStructured ? (
              <Database className="w-4 h-4" />
            ) : (
              <FileText className="w-4 h-4" />
            )}
          </span>

          {index !== undefined && (
            <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-900 text-white font-mono">
              [{index + 1}]
            </span>
          )}

          <span className="font-mono font-bold text-slate-900 text-sm truncate" title={evidence.evidence_id}>
            {evidence.evidence_id}
          </span>

          <span
            className={`px-2 py-0.5 rounded text-xs font-mono font-bold uppercase ${
              isSpatial
                ? "bg-cyan-100 text-cyan-900"
                : isGeology
                ? "bg-purple-100 text-purple-900"
                : isStructured
                ? "bg-blue-100 text-blue-900"
                : "bg-slate-100 text-slate-800"
            }`}
          >
            {isSpatial ? "SPATIAL" : isGeology ? "GEOLOGY" : isStructured ? "STRUCTURED" : "DOCUMENT"}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {onInspect && (
            <button
              type="button"
              onClick={() => onInspect(evidence.evidence_id)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-900 text-white hover:bg-blue-800 transition cursor-pointer shadow-2xs"
            >
              <span>Inspect</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          )}

          {evidence.snippet && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-slate-500 hover:text-slate-800 p-1.5 rounded-md hover:bg-slate-100 transition cursor-pointer"
              aria-label={isExpanded ? "Collapse" : "Expand"}
            >
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Metadata Pill Grid */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs sm:text-sm text-slate-700 pt-1.5 border-t border-slate-100">
        {evidence.mine_code && (
          <span className="flex items-center gap-1">
            <Building className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Mine:</span>{" "}
            <strong className="text-slate-900">{evidence.mine_code}</strong>
          </span>
        )}

        {evidence.source_name && (
          <span className="flex items-center gap-1">
            <FileText className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Source:</span>{" "}
            <strong className="text-slate-900 font-mono text-xs">{evidence.source_name}</strong>
          </span>
        )}

        {evidence.department && (
          <span className="flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Dept:</span>{" "}
            <strong className="text-slate-900">{evidence.department}</strong>
          </span>
        )}

        {evidence.page_number && (
          <span className="flex items-center gap-1">
            <Hash className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Page:</span>{" "}
            <strong className="text-slate-900">{evidence.page_number}</strong>
          </span>
        )}
      </div>

      {/* SPATIAL ATTRIBUTES CARD (if spatial evidence) */}
      {isSpatial && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            <div>
              <span className="text-slate-500 block font-medium">Layer</span>
              <span className="font-mono font-bold text-slate-800 truncate block">
                {evidence.layer_name || "spatial_layer"}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block font-medium">Feature ID</span>
              <span className="font-mono font-bold text-slate-800 truncate block">
                {evidence.feature_id || evidence.evidence_id}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block font-medium">Operation</span>
              <span className="font-bold text-slate-800 truncate block">
                {evidence.operation || "ST_DWithin"}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block font-medium">Distance</span>
              <span className="font-bold text-slate-800 truncate block">
                {evidence.distance_meters !== undefined && evidence.distance_meters !== null
                  ? `${evidence.distance_meters.toFixed(1)} m`
                  : "Within Boundary"}
              </span>
            </div>
          </div>

          {/* Lightweight Spatial Preview Indicator */}
          <div className="pt-2 border-t border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-slate-700 font-mono">
              <Compass className="w-4 h-4 text-blue-900 shrink-0" />
              {evidence.coordinates ? (
                <span>
                  WGS84: {Number(evidence.coordinates.longitude).toFixed(4)}°E,{" "}
                  {Number(evidence.coordinates.latitude).toFixed(4)}°N
                </span>
              ) : (
                <span>EPSG:4326 PostGIS Geometry</span>
              )}
            </div>

            {/* Micro SVG Radar Preview */}
            <div className="flex items-center gap-1.5" title="Spatial Proximity Indicator">
              <svg className="w-16 h-7" viewBox="0 0 64 28">
                <circle cx="32" cy="14" r="12" fill="none" stroke="#93c5fd" strokeWidth="1" strokeDasharray="2,2" />
                <circle cx="32" cy="14" r="6" fill="none" stroke="#60a5fa" strokeWidth="1" />
                <circle cx="32" cy="14" r="2.5" fill="#1e3a8a" />
                {evidence.distance_meters !== undefined && evidence.distance_meters !== null && (
                  <circle
                    cx={32 + Math.min(10, (evidence.distance_meters / 500) * 10)}
                    cy="14"
                    r="2"
                    fill="#059669"
                  />
                )}
              </svg>
            </div>
          </div>
        </div>
      )}

      {/* Snippet / Excerpt without quotes */}
      {evidence.snippet && (
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-slate-800 text-xs sm:text-sm leading-relaxed font-sans">
          <p className={isExpanded ? "" : "line-clamp-2"}>
            {evidence.snippet.replace(/^["'“”]|["'“”]$/g, "")}
          </p>
        </div>
      )}

      {/* Citation Ref */}
      {evidence.citation && (
        <div className="text-xs text-slate-600 flex items-center justify-between">
          <span className="truncate font-medium">Ref: {evidence.citation}</span>
          <span className="font-mono text-xs font-semibold text-slate-500 shrink-0 ml-2">Scope Verified</span>
        </div>
      )}
    </div>
  );
}
