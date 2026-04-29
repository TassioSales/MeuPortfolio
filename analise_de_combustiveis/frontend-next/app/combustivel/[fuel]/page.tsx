import { notFound } from "next/navigation";

import { DashboardClient } from "@/components/dashboard-client";

const fuels = new Set(["gasolina", "etanol", "diesel", "glp", "gnv"]);

export default async function CombustivelPage({
  params,
}: {
  params: Promise<{ fuel: string }>;
}) {
  const { fuel } = await params;
  if (!fuels.has(fuel)) {
    notFound();
  }
  return <DashboardClient pageMode="combustivel" initialFuel={fuel as "gasolina" | "etanol" | "diesel" | "glp" | "gnv"} />;
}
