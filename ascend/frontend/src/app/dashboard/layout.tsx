"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAuthStore } from "@/lib/stores/authStore";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token, user, loadUser } = useAuthStore();

  useEffect(() => {
    if (!token) { router.replace("/login"); return; }
    if (!user) loadUser();
  }, [token, user, loadUser, router]);

  if (!token) return null;

  return (
    <div className="flex min-h-screen bg-surface text-text-primary">
      <Sidebar />
      <main className="flex-1 overflow-hidden min-w-0">{children}</main>
    </div>
  );
}
