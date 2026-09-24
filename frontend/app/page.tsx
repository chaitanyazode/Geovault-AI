"use client";

import React from "react";
import Link from "next/link";
import {
  MessageSquare,
  FileText,
  CloudSun,
  ArrowRight,
} from "lucide-react";

export default function HomePage() {
  return (
    <div className="h-full flex-1 flex flex-col justify-between gap-4 lg:gap-5 min-h-0">
      {/* ========================================================================= */}
      {/* 1. TOP 50%: ENTERPRISE HERO (Brand Name & Taglines in Coal Gray Box)    */}
      {/* ========================================================================= */}
      <div className="relative flex-1 basis-1/2 min-h-0 bg-gradient-to-r from-[#1E222A] via-[#212630] to-[#252B36] border border-[#2C323E] rounded-2xl p-5 sm:p-6 lg:p-8 text-white shadow-xl flex flex-col justify-center overflow-hidden">
        {/* Subtle background radial glow */}
        <div className="absolute right-0 top-0 w-96 h-full bg-radial from-slate-500/10 to-transparent pointer-events-none" />

        <div className="relative z-10 max-w-4xl space-y-3 lg:space-y-3.5">
          {/* Brand Name */}
          <div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-white leading-none">
              GeoVault <span className="text-[#1E8E5A]">AI</span>
            </h1>
          </div>

          {/* Subtitle / Second Line */}
          <div className="text-base sm:text-lg lg:text-xl font-bold tracking-wide text-slate-200">
            Intelligent Decision Support for the Mining Enterprise
          </div>

          {/* Descriptive Lines (Smaller than second line) */}
          <div className="space-y-1 text-xs sm:text-sm lg:text-base text-slate-300/90 leading-relaxed max-w-3xl font-medium">
            <div>
              AI-powered intelligence for geological, mining and operational data.
            </div>
            <div>
              Ask questions, uncover insights, and generate evidence-grounded reports.
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 2. BOTTOM 50%: THREE COMPACT CAPABILITY CARDS (No Extra White Space)      */}
      {/* ========================================================================= */}
      <div className="flex-1 basis-1/2 min-h-0 grid grid-cols-1 md:grid-cols-3 gap-4 lg:gap-5">
        {/* Card 01: Ask GeoVault (Natural Query & Spatial Intelligence) */}
        <Link
          href="/ask"
          className="bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 flex flex-col justify-between hover:shadow-lg hover:border-slate-400/80 transition-all duration-150 group h-full shadow-2xs"
        >
          <div>
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-900 flex items-center justify-center font-bold shadow-2xs group-hover:bg-blue-900 group-hover:text-white transition-colors">
                <MessageSquare className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 group-hover:text-blue-900 transition-colors">
                01 &bull; Ask GeoVault
              </span>
            </div>

            <h2 className="text-base sm:text-lg lg:text-xl font-bold text-slate-900 mt-2 mb-1 group-hover:text-blue-950">
              Query Intelligence
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 leading-snug line-clamp-2 sm:line-clamp-3">
              Natural-language questions routed to SQL, RAG, PostGIS spatial queries, or Hybrid reasoning with verifiable source citations.
            </p>
          </div>

          <div className="pt-2 mt-auto border-t border-slate-100 flex items-center justify-end text-xs">
            <span className="inline-flex items-center gap-1.5 text-blue-900 font-bold group-hover:translate-x-1 transition-transform">
              <span>Open</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </Link>

        {/* Card 02: Topics & Word Cloud (NLP Corpus Mining) */}
        <Link
          href="/topics"
          className="bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 flex flex-col justify-between hover:shadow-lg hover:border-amber-900/40 transition-all duration-150 group h-full shadow-2xs"
        >
          <div>
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-800 flex items-center justify-center font-bold shadow-2xs group-hover:bg-amber-800 group-hover:text-white transition-colors">
                <CloudSun className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 group-hover:text-amber-800 transition-colors">
                02 &bull; Discovery
              </span>
            </div>

            <h2 className="text-base sm:text-lg lg:text-xl font-bold text-slate-900 mt-2 mb-1 group-hover:text-amber-950">
              Topics &amp; Word Cloud
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 leading-snug line-clamp-2 sm:line-clamp-3">
              Automated TF-IDF terminology mining, topic clustering, and word clouds generated exclusively from user authorized documents.
            </p>
          </div>

          <div className="pt-2 mt-auto border-t border-slate-100 flex items-center justify-end text-xs">
            <span className="inline-flex items-center gap-1.5 text-amber-900 font-bold group-hover:translate-x-1 transition-transform">
              <span>Explore</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </Link>

        {/* Card 03: Report Generator (Deterministic Institutional Reports) */}
        <Link
          href="/reports"
          className="bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 flex flex-col justify-between hover:shadow-lg hover:border-emerald-900/40 transition-all duration-150 group h-full shadow-2xs"
        >
          <div>
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-800 flex items-center justify-center font-bold shadow-2xs group-hover:bg-emerald-800 group-hover:text-white transition-colors">
                <FileText className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 group-hover:text-emerald-800 transition-colors">
                03 &bull; Reporting
              </span>
            </div>

            <h2 className="text-base sm:text-lg lg:text-xl font-bold text-slate-900 mt-2 mb-1 group-hover:text-emerald-950">
              Report Generator
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 leading-snug line-clamp-2 sm:line-clamp-3">
              Synthesize 4-page publication-grade PDF and DOCX reports with exact tables, KPI metrics, chart trends, and verifiable evidence references.
            </p>
          </div>

          <div className="pt-2 mt-auto border-t border-slate-100 flex items-center justify-end text-xs">
            <span className="inline-flex items-center gap-1.5 text-emerald-900 font-bold group-hover:translate-x-1 transition-transform">
              <span>Generate</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </span>
          </div>
        </Link>
      </div>
    </div>
  );
}
