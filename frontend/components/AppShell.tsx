"use client";

import React, { useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<string>("USR001");

  const handleUserChanged = (newUserId: string) => {
    setCurrentUser(newUserId);
    // Reload page to re-fetch all active scoped datasets with new X-User-ID
    window.location.reload();
  };

  return (
    <div className="h-screen bg-[#F4F6F9] text-slate-900 antialiased font-sans flex flex-col overflow-hidden">
      {/* Top Institutional Header spanning 100% width */}
      <Header onUserChanged={handleUserChanged} />

      {/* Main Two-Column Layout */}
      <div className="flex-1 flex min-w-0 overflow-hidden">
        <Sidebar />
        <main className="flex-1 p-4 sm:px-6 sm:py-4 lg:px-8 lg:py-5 overflow-y-auto min-w-0 max-w-7xl mx-auto w-full flex flex-col h-full">
          {children}
        </main>
      </div>
    </div>
  );
}
