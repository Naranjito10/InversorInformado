import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchZones, runSearch } from "../services/api";
import type { SearchRequest, SearchResponse } from "../types";

const PORTALES = ["idealista", "fotocasa", "habitaclia", "pisos", "casaradar"];
const PAGINAS = [10, 20, 50, 100];

const initialForm: SearchRequest = {
  zona: "",
  precio_min: undefined,
  precio_max: undefined,
  portales: [],
  max_pages: 10,
};

export default function SearchForm() {
  const [form, setForm] = useState<SearchRequest>(initialForm);
  const [result, setResult] = useState<SearchResponse | null>(null);

  const zonesQuery = useQuery({ queryKey: ["zones"], queryFn: fetchZones });

  const searchMutation = useMutation({
    mutationFn: runSearch,
    onSuccess: (data) => setResult(data),
  });

  const togglePortal = (portal: string) => {
    setForm((f) => ({
      ...f,
      portales: f.portales.includes(portal)
        ? f.portales.filter((p) => p !== portal)
        : [...f.portales, portal],
    }));
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setResult(null);
    searchMutation.mutate(form);
  };

  const isValid = form.zona && form.portales.length > 0;

  return (
    <div className="mx-auto flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Buscar oportunidades</h1>
        <p className="text-sm text-gray-400 mt-1">
          Lanza una búsqueda personalizada por zona y portales
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col gap-5">

        {/* Zona */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">
            Zona <span className="text-red-500">*</span>
          </label>
          <input
            list="zones-list"
            required
            placeholder="Escribe para buscar zona..."
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={form.zona}
            onChange={(e) => setForm((f) => ({ ...f, zona: e.target.value }))}
          />
          <datalist id="zones-list">
            {zonesQuery.data?.map((z) => (
              <option key={z.key} value={z.label} />
            ))}
          </datalist>
        </div>

        {/* Precios */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700">
              Precio mínimo (€) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              required
              min={0}
              placeholder="Ej: 100000"
              className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.precio_min ?? ""}
              onChange={(e) =>
                setForm((f) => ({ ...f, precio_min: e.target.value ? Number(e.target.value) : undefined }))
              }
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700">
              Precio máximo (€) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              required
              min={0}
              placeholder="Ej: 300000"
              className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.precio_max ?? ""}
              onChange={(e) =>
                setForm((f) => ({ ...f, precio_max: e.target.value ? Number(e.target.value) : undefined }))
              }
            />
          </div>
        </div>

        {/* Portales */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700">
            Portales <span className="text-red-500">*</span>
          </label>
          <div className="flex flex-wrap gap-3">
            {PORTALES.map((portal) => {
              const available =
                !form.zona ||
                (zonesQuery.data
                  ?.find((z) => z.label === form.zona)
                  ?.portales_disponibles.includes(portal) ??
                true);
              const selected = form.portales.includes(portal);
              return (
                <button
                  key={portal}
                  type="button"
                  disabled={!available}
                  onClick={() => togglePortal(portal)}
                  className={`px-4 py-2 rounded-lg text-sm border transition-colors capitalize
                    ${selected
                      ? "bg-blue-600 text-white border-blue-600"
                      : available
                      ? "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                      : "bg-gray-50 text-gray-300 border-gray-200 cursor-not-allowed"
                    }`}
                >
                  {portal === "pisos" ? "Pisos.com" : portal.charAt(0).toUpperCase() + portal.slice(1)}
                  {!available && " (n/d)"}
                </button>
              );
            })}
          </div>
          {form.zona && (
            <p className="text-xs text-gray-400">
              Los portales en gris no están disponibles para esta zona.
            </p>
          )}
        </div>

        {/* Páginas por portal */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Páginas por portal</label>
          <div className="flex gap-2">
            {PAGINAS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setForm((f) => ({ ...f, max_pages: p }))}
                className={`px-4 py-2 rounded-lg text-sm border transition-colors
                  ${form.max_pages === p
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                  }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={!isValid || searchMutation.isPending}
          className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {searchMutation.isPending ? "Lanzando búsqueda..." : "Buscar ahora"}
        </button>
      </form>

      {/* Resultado */}
      {searchMutation.isError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          Error al lanzar la búsqueda. Verifica que la zona tenga portales disponibles.
        </div>
      )}

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <p className="font-medium text-green-800 mb-3">
            Búsqueda lanzada — {result.targets} target{result.targets !== 1 ? "s" : ""} en cola
          </p>
          <p className="text-sm text-green-700 mb-2">
            <span className="font-medium">Zona:</span> {result.zona}
          </p>
          <p className="text-sm text-green-700 mb-3">
            <span className="font-medium">Portales:</span> {result.portales.join(", ")}
          </p>
          <div className="flex flex-col gap-1">
            <p className="text-xs text-green-600 font-medium">URLs que se van a scrapear:</p>
            {result.search_urls.map((url, i) => (
              <a
                key={i}
                href={url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-blue-600 hover:underline truncate"
              >
                {url}
              </a>
            ))}
          </div>
          <p className="text-xs text-green-600 mt-3">
            Los resultados aparecerán en el Dashboard en unos minutos.
          </p>
        </div>
      )}
    </div>
  );
}