"use client";

import React, { useEffect, useState } from "react";
import { ChevronDown, Check, Bell } from "lucide-react";
import { ApiClient, getActiveUserId, setActiveUserId } from "../lib/api";
import { DemoUserOption, UserProfileResponse } from "../lib/types";

interface HeaderProps {
  onUserChanged?: (userId: string) => void;
}

export default function Header({ onUserChanged }: HeaderProps) {
  const [users, setUsers] = useState<DemoUserOption[]>([]);
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [activeId, setActiveId] = useState<string>(getActiveUserId());
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const loadData = async (userId: string) => {
    try {
      const [allUsers, prof] = await Promise.all([
        ApiClient.getUsers(),
        ApiClient.getUserProfile(),
      ]);
      setUsers(allUsers);
      setProfile(prof);
    } catch (err) {
      console.error("Failed to load user profile in Header:", err);
    }
  };

  useEffect(() => {
    loadData(activeId);
  }, [activeId]);

  const handleSelectUser = (uId: string) => {
    setActiveId(uId);
    setActiveUserId(uId);
    setIsDropdownOpen(false);
    if (onUserChanged) {
      onUserChanged(uId);
    } else {
      window.location.reload();
    }
  };

  // Compute initials for the avatar badge from role or username
  const getUserInitials = (userId: string, role?: string, name?: string) => {
    if (name && name.length >= 2) {
      const parts = name.trim().split(/\s+/);
      if (parts.length >= 2) {
        return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      }
      return name.slice(0, 2).toUpperCase();
    }
    if (role?.includes("Mining")) return "ME";
    if (role?.includes("Geology")) return "GE";
    if (role?.includes("Transportation")) return "TE";
    if (role?.includes("Manager")) return "MM";
    if (role?.includes("Admin")) return "AD";
    return userId.slice(0, 2).toUpperCase();
  };

  const formatScopeMines = (
    allowedMines: string[] | string | null | undefined,
    assignedMine?: string
  ): string => {
    if (allowedMines === null || allowedMines === "ALL") {
      return "All Authorized Mines";
    }
    if (typeof allowedMines === "string") {
      return allowedMines.toUpperCase() === "ALL" ? "All Authorized Mines" : allowedMines;
    }
    if (Array.isArray(allowedMines)) {
      if (allowedMines.length === 0) {
        return assignedMine || "Authorized Scope";
      }
      if (allowedMines.length === 1) {
        return allowedMines[0].toUpperCase() === "ALL" ? "All Authorized Mines" : allowedMines[0];
      }
      if (allowedMines.length === 2) {
        return `${allowedMines[0]} & ${allowedMines[1]}`;
      }
      return `${allowedMines.length} Mines Authorized`;
    }
    return assignedMine || "Authorized Scope";
  };

  const dynamicScopeLabel = formatScopeMines(
    profile?.scope?.allowed_mines ?? profile?.authorized_scope?.allowed_mines,
    profile?.user?.assigned_mine_code
  );
  const activeDisplayName = profile?.user?.full_name || profile?.user?.username || activeId;
  const activeRole = profile?.user?.role || "Authorized Engineer";

  return (
    <header className="bg-white border-b border-slate-200/80 sticky top-0 z-40 shadow-xs h-[96px] lg:h-[105px] flex items-center w-full">
      <div className="px-6 sm:px-10 lg:px-12 w-full flex items-center justify-between gap-6">
        {/* Left: Dual Clean Institutional Logos + GeoVault AI Title */}
        <div className="flex items-center gap-6 sm:gap-8 lg:gap-10 h-full">
          {/* Ministry of Coal / Government of India (Clean Logo) */}
          <div className="flex items-center h-full">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/ministry_of_coal_clean.png"
              alt="Government of India — Ministry of Coal"
              className="h-16 lg:h-20 w-auto max-h-[75px] lg:max-h-[85px] object-contain shrink-0"
            />
          </div>

          {/* Coal India Limited (Clean Logo) */}
          <div className="flex items-center h-full">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/coal_india_clean.png"
              alt="Coal India Limited — A Maharatna Company"
              className="h-16 lg:h-20 w-auto max-h-[75px] lg:max-h-[85px] object-contain shrink-0"
            />
          </div>

          {/* GeoVault AI Product Identity beside Logos */}
          <div className="hidden sm:block leading-tight border-l-2 border-slate-200 pl-5">
            <div className="font-black text-4xl lg:text-5xl tracking-tight text-[#0F1E36]">
              GeoVault <span className="text-[#1E8E5A]">AI</span>
            </div>
            <div className="text-sm lg:text-base text-slate-500 font-bold tracking-wide mt-1">
              CMPDI &bull; Coal India
            </div>
          </div>
        </div>

        {/* Right: Notification Icon, User Profile & Scope */}
        <div className="flex flex-col items-end">
          <div className="flex items-center gap-3.5 sm:gap-4">
            {/* Notification Bell */}
            <button
              type="button"
              className="p-2 rounded-full hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition relative cursor-pointer"
              title="Notifications"
            >
              <Bell className="w-5 h-5 stroke-[1.8]" />
              <span className="w-2 h-2 rounded-full bg-blue-700 absolute top-2 right-2 ring-2 ring-white"></span>
            </button>

            {/* User Profile Dropdown Button */}
            <div className="relative">
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center gap-3 p-1.5 sm:px-3 sm:py-1.5 rounded-lg hover:bg-slate-50 border border-slate-200 text-left transition cursor-pointer"
              >
                {/* Initials Avatar */}
                <div className="w-10 h-10 rounded-full bg-[#10223D] text-white flex items-center justify-center font-bold text-sm shadow-2xs shrink-0">
                  {getUserInitials(activeId, profile?.user?.role, profile?.user?.full_name)}
                </div>

                <div className="hidden sm:block leading-tight text-right">
                  <div className="text-sm font-bold text-slate-900">
                    {activeDisplayName}
                  </div>
                  <div className="text-xs text-slate-500 font-medium mt-0.5">
                    {activeRole}
                  </div>
                </div>

                <ChevronDown className="w-4 h-4 text-slate-500 shrink-0" />
              </button>

              {/* User Switcher Dropdown */}
              {isDropdownOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-xl shadow-xl py-2 z-50 text-xs">
                  <div className="px-3 py-1.5 border-b border-slate-100 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Switch Active User (RBAC / ABAC)
                  </div>
                  <div className="p-1 space-y-1">
                    {users.map((u) => {
                      const isSelected = u.user_id === activeId;

                      return (
                        <button
                          key={u.user_id}
                          onClick={() => handleSelectUser(u.user_id)}
                          className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between transition ${
                            isSelected
                              ? "bg-blue-50 text-blue-900 font-semibold"
                              : "text-slate-700 hover:bg-slate-50"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <div className="w-8 h-8 rounded-full bg-[#10223D] text-white flex items-center justify-center font-bold text-xs shrink-0">
                              {getUserInitials(u.user_id, u.role, u.name)}
                            </div>
                            <div className="min-w-0">
                              <div className="font-bold text-slate-900 text-sm truncate">
                                {u.name || u.user_id} ({u.user_id})
                              </div>
                              <div className="text-xs text-slate-500 truncate">
                                {u.role}
                              </div>
                            </div>
                          </div>
                          {isSelected && <Check className="w-4 h-4 text-blue-900 shrink-0 ml-2" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
