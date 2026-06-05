import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchZones, runSearch, fetchFuentes } from "../services/api";
import type { SearchRequest, SearchResponse } from "../types";
import Modal from "../components/Modal";

const PAGINAS = [10, 20, 50, 100];

const initialForm: SearchRequest = {
  zona: "",
  precio_min: undefined,
  precio_max: undefined,
  portales: [],
  max_pages: 10,
};

export default function SearchForm() {
  const qc = useQueryClient();
  const [form, setForm] = useState<SearchRequest>(initialForm);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [zonaInput, setZonaInput] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const comboRef = useRef<HTMLDivElement>(null);

  const zonesQuery = useQuery({ queryKey: ["zones"], queryFn: fetchZones });
  const { data: fuentes = [] } = useQuery({
    queryKey: ["fuentes"],
    queryFn: () => fetchFuentes(),
    staleTime: 60_000,
  });
  const portales = fuentes.filter((f) => f.activo && f.id !== "manual");

  const zonasSugeridas = zonaInput.trim().length === 0
    ? (zonesQuery.data ?? [])
    : (zonesQuery.data ?? []).filter((z) =>
        z.label.toLowerCase().includes(zonaInput.toLowerCase())
      );

  const zoneMatch = zonesQuery.data?.find((z) => z.label === form.zona);

  // Cerrar dropdown al hacer click fuera
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (comboRef.current && !comboRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const selectZona = (label: string) => {
    setForm((f) => ({ ...f, zona: label, portales: [] }));
    setZonaInput(label);
    setShowDropdown(false);
  };

  const handleZonaInput = (value: string) => {
    setZonaInput(value);
    setForm((f) => ({ ...f, zona: "", portales: [] }));
    setShowDropdown(true);
  };

  const searchMutation = useMutation({
    mutationFn: runSearch,
    onSuccess: (data) => {
      setResult(data);
      qc.invalidateQueries({ queryKey: ["scraper-status"] });
    },
  });

  const handleAccept = () => {
    setResult(null);
    setForm(initialForm);
    setZonaInput("");
  };

  const togglePortal = (portal: string) => {
    setForm((f) => ({
      ...f,
      portales: f.portales.includes(portal)
        ? f.portales.filter((p) => p !== portal)
        : [...f.portales, portal],
    }));
  };

  const handleSubmit = (e: { preventDefault(): void }) => {
    e.preventDefault();
    setResult(null);
    searchMutation.mutate(form);
  };

  const isValid = form.zona && form.portales.length > 0;

  const errorDetail = (() => {
    const err = searchMutation.error as { response?: { data?: { detail?: string } } } | null;
    return err?.response?.data?.detail ?? null;
  })();

  return (
    <div className="mx-auto flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Buscar oportunidades</h1>
        <p className="text-sm text-gray-400 mt-1">
          Lanza una búsqueda personalizada por zona y portales
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col gap-5">

        {/* Zona — combobox */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">
            Zona <span className="text-red-500">*</span>
          </label>
          <div ref={comboRef} className="relative">
            <input
              type="text"
              required
              autoComplete="off"
              placeholder="Escribe para filtrar zonas..."
              className={`w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                zonaInput && !form.zona ? "border-yellow-400" : "border-gray-300"
              }`}
              value={zonaInput}
              onChange={(e) => handleZonaInput(e.target.value)}
              onFocus={() => setShowDropdown(true)}
            />
            {showDropdown && zonasSugeridas.length > 0 && (
              <ul className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-56 overflow-y-auto">
                {zonasSugeridas.map((z) => (
                  <li
                    key={z.key}
                    onMouseDown={() => selectZona(z.label)}
                    className="px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 cursor-pointer"
                  >
                    {z.label}
                  </li>
                ))}
              </ul>
            )}
            {showDropdown && zonaInput.trim() && zonasSugeridas.length === 0 && (
              <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm text-gray-400">
                No hay zonas que coincidan con "{zonaInput}"
              </div>
            )}
          </div>
          {zonaInput && !form.zona && (
            <p className="text-xs text-yellow-700">Selecciona una zona de la lista.</p>
          )}
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
            {portales.map((f) => {
              const available =
                !form.zona ||
                !zoneMatch ||
                zoneMatch.portales_disponibles.includes(f.id);
              const selected = form.portales.includes(f.id);
              return (
                <button
                  key={f.id}
                  type="button"
                  disabled={!available}
                  onClick={() => togglePortal(f.id)}
                  className={`px-4 py-2 rounded-lg text-sm border transition-colors
                    ${selected
                      ? "bg-blue-600 text-white border-blue-600"
                      : available
                      ? "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
                      : "bg-gray-50 text-gray-300 border-gray-200 cursor-not-allowed"
                    }`}
                >
                  {f.nombre}
                  {!available && " (n/d)"}
                </button>
              );
            })}
          </div>
          {zoneMatch && (
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

      {searchMutation.isError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {errorDetail ?? "Error al lanzar la búsqueda."}
        </div>
      )}

      <Modal
        isOpen={result !== null}
        onClose={handleAccept}
        title="Búsqueda lanzada"
        maxWidth="max-w-lg"
      >
        {result && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-gray-700">
              <span className="font-medium">{result.targets} target{result.targets !== 1 ? "s" : ""}</span> en cola para scraping.
            </p>
            <div className="flex flex-col gap-1 text-sm text-gray-700">
              <p><span className="font-medium">Zona:</span> {result.zona}</p>
              <p><span className="font-medium">Portales:</span> {result.portales.join(", ")}</p>
            </div>
            <div className="flex flex-col gap-1">
              <p className="text-xs font-medium text-gray-500">URLs que se van a scrapear:</p>
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
            <p className="text-xs text-gray-400">Los resultados aparecerán en el Dashboard en unos minutos.</p>
            <div className="flex justify-end pt-1">
              <button
                onClick={handleAccept}
                className="px-5 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
              >
                Aceptar
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
