import { useRef, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ListingFilters, ZonaOption } from "../services/api";
import { fetchFuentes, fetchListingZonas } from "../services/api";

interface Props {
  filters: ListingFilters;
  onChange: (f: ListingFilters) => void;
}

const LABELS = ["alto", "medio", "normal", "incompleto"];

export default function Filters({ filters, onChange }: Props) {
  const set = (key: keyof ListingFilters, value: unknown) =>
    onChange({ ...filters, [key]: value || undefined });

  const { data: fuentes = [] } = useQuery({
    queryKey: ["fuentes"],
    queryFn: () => fetchFuentes(),
    staleTime: 60_000,
  });

  const { data: zonas = [] } = useQuery({
    queryKey: ["listing-zonas"],
    queryFn: fetchListingZonas,
    staleTime: 120_000,
  });

  // Zona combobox state
  const activeZonaLabel =
    filters.barrio
      ? zonas.find((z) => z.tipo === "barrio" && z.valor === filters.barrio)?.label ?? filters.barrio
      : filters.municipio
      ? filters.municipio
      : "";

  const [zonaInput, setZonaInput] = useState(activeZonaLabel);
  const [showDropdown, setShowDropdown] = useState(false);
  const comboRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setZonaInput(activeZonaLabel);
  }, [activeZonaLabel]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (comboRef.current && !comboRef.current.contains(e.target as Node))
        setShowDropdown(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtered = zonaInput.trim()
    ? zonas.filter((z) => z.label.toLowerCase().includes(zonaInput.toLowerCase()))
    : zonas;

  const selectZona = (z: ZonaOption) => {
    const next: ListingFilters = { ...filters, municipio: undefined, barrio: undefined };
    if (z.tipo === "municipio") next.municipio = z.valor;
    else next.barrio = z.valor;
    onChange(next);
    setZonaInput(z.label);
    setShowDropdown(false);
  };

  const clearZona = () => {
    onChange({ ...filters, municipio: undefined, barrio: undefined });
    setZonaInput("");
    setShowDropdown(false);
  };

  const handleZonaInput = (val: string) => {
    setZonaInput(val);
    if (!val) clearZona();
    else onChange({ ...filters, municipio: undefined, barrio: undefined });
    setShowDropdown(true);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm flex flex-wrap gap-3 items-end">

      {/* Zona combobox */}
      <div className="flex flex-col gap-1 flex-1 min-w-[220px]">
        <label className="text-xs text-gray-500">Zona</label>
        <div ref={comboRef} className="relative">
          <input
            type="text"
            autoComplete="off"
            placeholder="Municipio o barrio..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-7"
            value={zonaInput}
            onChange={(e) => handleZonaInput(e.target.value)}
            onFocus={() => setShowDropdown(true)}
          />
          {zonaInput && (
            <button
              type="button"
              onClick={clearZona}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500"
            >
              ×
            </button>
          )}
          {showDropdown && filtered.length > 0 && (
            <ul className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {filtered.map((z, i) => (
                <li
                  key={i}
                  onMouseDown={() => selectZona(z)}
                  className="flex items-center justify-between px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 cursor-pointer"
                >
                  <span>{z.label}</span>
                  <span className="text-xs text-gray-400 ml-2 shrink-0">
                    {z.tipo === "municipio" ? "Municipio" : "Barrio"}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {showDropdown && zonaInput.trim() && filtered.length === 0 && (
            <div className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm text-gray-400">
              Sin resultados
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs text-gray-500">Portal</label>
        <select
          className="capitalize border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={filters.fuente ?? ""}
          onChange={(e) => set("fuente", e.target.value)}
        >
          <option value="">Todos</option>
          {fuentes.map((f) => <option key={f.id} value={f.id}>{f.nombre}</option>)}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs text-gray-500">Score label</label>
        <select
          className="capitalize border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
        onClick={() => { onChange({}); setZonaInput(""); }}
      >
        Limpiar
      </button>
    </div>
  );
}
