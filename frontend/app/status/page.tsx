"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  Server,
  Database,
  Cpu,
  ShieldCheck,
  RefreshCw,
  Layers,
  FileCheck2,
} from "lucide-react";
import { ApiClient } from "../../lib/api";
import { DemoUserOption, SystemHealth } from "../../lib/types";

export default function SystemStatusPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [users, setUsers] = useState<DemoUserOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<string>("");

  const refreshHealth = async () => {
    setLoading(true);
    try {
      const [h, u] = await Promise.all([
        ApiClient.getHealth(),
        ApiClient.getUsers(),
      ]);
      setHealth(h);
      setUsers(u);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Health fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshHealth();
    const interval = setInterval(refreshHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status?: string) => {
    const isHealthy = status === "healthy" || status === "ok";
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full ${
          isHealthy
            ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
            : "bg-amber-50 text-amber-800 border border-amber-200"
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isHealthy ? "bg-emerald-600" : "bg-amber-600"
          }`}
        ></span>
        {isHealthy ? "Healthy" : status?.toUpperCase() || "Checking"}
      </span>
    );
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            System Status
          </h1>
          <p className="text-sm sm:text-base text-slate-600 mt-1">
            Status of core services, operational database, and local LLM runtime.
          </p>
        </div>

        <button
          onClick={refreshHealth}
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-white hover:bg-slate-50 text-slate-800 text-sm font-bold flex items-center gap-2 border border-slate-300 transition shadow-xs self-start sm:self-auto cursor-pointer"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh ({lastRefreshed || "Now"})</span>
        </button>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Backend */}
        <div className="bg-white border border-slate-200 p-5 rounded-xl shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <Server className="w-5 h-5 text-blue-900" />
              {getStatusBadge(health?.backend)}
            </div>
            <h2 className="text-lg font-bold text-slate-900">Backend API</h2>
            <p className="text-sm text-slate-600 mt-1">FastAPI REST Server &amp; Intelligence Router</p>
          </div>
          <div className="text-xs sm:text-sm text-slate-600 font-mono font-semibold mt-4 pt-3 border-t border-slate-100">
            Python 3.12+ • Port 8000
          </div>
        </div>

        {/* PostgreSQL */}
        <div className="bg-white border border-slate-200 p-5 rounded-xl shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <Database className="w-5 h-5 text-blue-900" />
              {getStatusBadge(health?.postgres)}
            </div>
            <h2 className="text-lg font-bold text-slate-900">PostgreSQL Database</h2>
            <p className="text-sm text-slate-600 mt-1">Structured Records, PostGIS Spatial &amp; pgvector</p>
          </div>
          <div className="text-xs sm:text-sm text-slate-600 font-mono font-semibold mt-4 pt-3 border-t border-slate-100">
            PostgreSQL 16 + PostGIS + pgvector
          </div>
        </div>

        {/* Redis */}
        <div className="bg-white border border-slate-200 p-5 rounded-xl shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <Activity className="w-5 h-5 text-blue-900" />
              {getStatusBadge(health?.redis)}
            </div>
            <h2 className="text-lg font-bold text-slate-900">Redis Broker</h2>
            <p className="text-sm text-slate-600 mt-1">In-Memory Cache &amp; Task Queue</p>
          </div>
          <div className="text-xs sm:text-sm text-slate-600 font-mono font-semibold mt-4 pt-3 border-t border-slate-100">
            Redis 7.0 • Port 6379
          </div>
        </div>

        {/* Local LLM */}
        <div className="bg-white border border-slate-200 p-5 rounded-xl shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <Cpu className="w-5 h-5 text-blue-900" />
              {getStatusBadge(health?.llm)}
            </div>
            <h2 className="text-lg font-bold text-slate-900">Local LLM Engine</h2>
            <p className="text-sm text-slate-600 mt-1">Qwen3-8B On-Premises Synthesis</p>
          </div>
          <div className="text-xs sm:text-sm text-slate-600 font-mono font-semibold mt-4 pt-3 border-t border-slate-100">
            llama.cpp GGUF • Offline
          </div>
        </div>

        {/* Background Worker */}
        <div className="bg-white border border-slate-200 p-5 rounded-xl shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <Layers className="w-5 h-5 text-blue-900" />
              {getStatusBadge(health?.backend ? "healthy" : "unavailable")}
            </div>
            <h2 className="text-lg font-bold text-slate-900">Celery Worker</h2>
            <p className="text-sm text-slate-600 mt-1">Background Report &amp; Topic Tasks</p>
          </div>
          <div className="text-xs sm:text-sm text-slate-600 font-mono font-semibold mt-4 pt-3 border-t border-slate-100">
            Celery 5.4+ Pipeline
          </div>
        </div>

        {/* Frontend */}
        <div className="bg-white border border-slate-200 p-5 rounded-xl shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <Server className="w-5 h-5 text-blue-900" />
              {getStatusBadge("healthy")}
            </div>
            <h2 className="text-lg font-bold text-slate-900">Web Application</h2>
            <p className="text-sm text-slate-600 mt-1">Next.js 14 Enterprise Portal</p>
          </div>
          <div className="text-xs sm:text-sm text-slate-600 font-mono font-semibold mt-4 pt-3 border-t border-slate-100">
            Port 3000 • Standalone
          </div>
        </div>
      </div>

      {/* Demo Identity Scope Reference */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs space-y-4">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-900" />
            Evaluation User Directory
          </h2>
          <p className="text-sm text-slate-600 mt-1">
            Configured test identities used to demonstrate Role-Based (RBAC) and Attribute-Based (ABAC) Access Control.
          </p>
        </div>

        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left text-sm border-collapse">
            <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200 text-xs uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">User ID</th>
                <th className="py-3 px-4">Name</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Department</th>
                <th className="py-3 px-4">Mine Scope</th>
                <th className="py-3 px-4">Clearance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {users.map((u) => (
                <tr key={u.user_id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-slate-900">{u.user_id}</td>
                  <td className="py-3 px-4 font-semibold text-slate-900">{u.name}</td>
                  <td className="py-3 px-4 text-slate-700">{u.role}</td>
                  <td className="py-3 px-4 text-slate-700">{u.department}</td>
                  <td className="py-3 px-4 font-mono text-slate-800 font-medium">{u.assigned_mine || "ALL"}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2.5 py-1 rounded text-xs font-bold border ${
                        u.clearance === "CONFIDENTIAL"
                          ? "bg-red-50 text-red-700 border-red-200"
                          : u.clearance === "RESTRICTED"
                          ? "bg-amber-50 text-amber-800 border-amber-200"
                          : "bg-emerald-50 text-emerald-800 border-emerald-200"
                      }`}
                    >
                      {u.clearance}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
