import type { Stats } from "../types";

interface Props {
  stats: Stats;
}

const Card = ({ label, value, sub }: { label: string; value: string | number; sub?: string }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
    <p className="text-sm text-gray-500">{label}</p>
    <p className="text-3xl font-bold text-gray-800 mt-1">{value}</p>
    {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
  </div>
);

export default function StatsCards({ stats }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card label="Anuncios activos" value={stats.total_activos} />
      <Card label="Nuevos esta semana" value={stats.nuevos_esta_semana} />
      <Card label="Score medio" value={stats.score_medio} sub="sobre 100" />
      <Card label="Bajadas de precio" value={stats.bajadas_precio} />
    </div>
  );
}