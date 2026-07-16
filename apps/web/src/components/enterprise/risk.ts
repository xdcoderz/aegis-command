export type RiskTier = "neutral" | "warning" | "danger";

export function riskTier(score: number): RiskTier {
  if (score >= 70) return "danger";
  if (score >= 40) return "warning";
  return "neutral";
}

export function riskLabel(score: number): string {
  const tier = riskTier(score);
  if (tier === "danger") return "Critical";
  if (tier === "warning") return "Elevated";
  return "Normal";
}

export function clampRisk(score: number): number {
  return Math.max(0, Math.min(100, Number.isFinite(score) ? score : 0));
}

export function formatCompactDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;

  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatClock(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
