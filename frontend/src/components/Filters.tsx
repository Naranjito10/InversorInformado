import type { ListingFilters } from "../services/api";

interface Props {
  filters: ListingFilters;
  onChange: (f: ListingFilters) => void;
}

const PORTALES = ["idealista", "fotocasa", "habitaclia", "pisos"];
const LABELS = ["alto", "medio", "normal", "incompleto"];

export default function Filters({ filters, onChange }: Props) {
  const set = (key: keyof ListingFilters, value: unknown) =>
    onChange({ ...filters, [key]: value || undefined });

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm flex flex-wrap gap-3 items-end">
      <div className="flex flex-col gap-1 min-w-[140px]">
        <label className="text-xs text-gray-500">Municipio</label>
        <input
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Barcelona..."
          value={filters.municipio ?? ""}
          onChange={(e) => set("municipio", e.target.value)}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs text-gray-500">Portal</label>
        <select
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={filters.fuente ?? ""}
          onChange={(e) => set("fuente", e.target.value)}
        >
          <option value="">Todos</option>
          {PORTALES.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs text-gray-500">Score label</label>
        <select
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={filters.score_label ?? ""}
          onChange={(e) => set("score_label", e.target.value)}
        >
          <option value="">Todos</option>
          {LABELS.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
      </div>

      <div className="flex flex-col gap-1 w-24">
        <label className="text-xs text-gray-500">Score mín.</label>
        <input
          type="number"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="0"
          value={filters.score_min ?? ""}
          onChange={(e) => set("score_min", e.target.value ? Number(e.target.value) : undefined)}
        />
      </div>

      <div className="flex flex-col gap-1 w-28">
        <label className="text-xs text-gray-500">Precio mín. (€)</label>
        <input
          type="number"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="0"
          value={filters.precio_min ?? ""}
          onChange={(e) => set("precio_min", e.target.value ? Number(e.target.value) : undefined)}
        />
      </div>

      <div className="flex flex-col gap-1 w-28">
        <label className="text-xs text-gray-500">Precio máx. (€)</label>
        <input
          type="number"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="999999"
          value={filters.precio_max ?? ""}
          onChange={(e) => set("precio_max", e.target.value ? Number(e.target.value) : undefined)}
        />
      </div>

      <button
        className="px-4 py-2 text-sm text-gray-500 hover:text-gray-800 border border-gray-300 rounded-lg"
        onClick={() => onChange({})}
      >
        Limpiar
      </button>
    </div>
  );
}