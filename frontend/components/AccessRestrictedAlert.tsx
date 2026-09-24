"use client";

import React from "react";
import { ShieldX, Lock, ArrowRight } from "lucide-react";

interface AccessRestrictedAlertProps {
  detail?: string;
  onSwitchUser?: () => void;
}

export default function AccessRestrictedAlert({ detail, onSwitchUser }: AccessRestrictedAlertProps) {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 my-4">
      <div className="flex items-start gap-3.5">
        <div className="w-10 h-10 rounded-lg bg-amber-100 border border-amber-200 flex items-center justify-center shrink-0">
          <ShieldX className="w-5 h-5 text-amber-800" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-base text-amber-900">
            Access Restricted
          </h3>

          <p className="text-sm text-slate-800 mt-1.5 leading-relaxed">
            {detail || "You do not have authorization to view records for this operational unit or department."}
          </p>

          <div className="mt-3 pt-3 border-t border-amber-200 flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm text-slate-700">
            <div className="flex items-center gap-1.5">
              <Lock className="w-4 h-4 text-slate-500" />
              <span>Permission-based access control is enforced prior to data retrieval.</span>
            </div>

            {onSwitchUser && (
              <button
                onClick={onSwitchUser}
                className="px-3.5 py-1.5 rounded-lg bg-blue-900 hover:bg-blue-800 text-white font-bold text-xs sm:text-sm flex items-center gap-1.5 transition shadow-xs cursor-pointer"
              >
                Switch User in Header <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
