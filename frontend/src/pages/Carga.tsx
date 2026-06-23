import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  bulkImport,
  checkUrls,
  createManualListing,
  fetchFuentes,
} from "../services/api";
import type { BulkImportResult, ManualListingIn } from "../services/api";

// ---------------------------------------------------------------------------
// CSV helpers
// ---------------------------------------------------------------------------

const CSV_HEADERS = [
  "url", "fuente", "titulo", "precio_venta", "metros_cuadrados",
  "habitaciones", "banos", "municipio", "barrio", "provincia",
  "condition", "ocupacion", "situacion_legal",
  "ascensor", "terraza", "garaje", "certificado_energetico",
  "alquiler_estimado", "precio_zona_m2",
];

const HEADER_LABELS: Record<string, string> = {
  url: "URL", fuente: "Fuente", titulo: "Título",
  precio_venta: "Precio (€)", metros_cuadrados: "M²",
  habitaciones: "Hab.", banos: "Baños", municipio: "Municipio",
  barrio: "Barrio", provincia: "Provincia",
  condition: "Condición", ocupacion: "Ocupación", situacion_legal: "Situación legal",
  ascensor: "Ascensor", terraza: "Terraza", garaje: "Garaje",
  certificado_energetico: "CEE", alquiler_estimado: "Alquiler est.",
  precio_zona_m2: "Precio zona/m²",
};

const INT_FIELDS = new Set(["precio_venta", "metros_cuadrados", "habitaciones", "banos", "alquiler_estimado", "precio_zona_m2"]);
const BOOL_FIELDS = new Set(["ascensor", "terraza", "garaje"]);
const BOOL_TRUE = new Set(["true", "1", "si", "sí", "yes", "s"]);

function splitLine(line: string): string[] {
  const result: string[] = [];
  let cur = "";
  let inQ = false;
  for (const ch of line) {
    if (ch === '"') { inQ = !inQ; }
    else if (ch === "," && !inQ) { result.push(cur.trim()); cur = ""; }
    else { cur += ch; }
  }
  result.push(cur.trim());
  return result;
}

function parseCSV(text: string): { headers: string[]; rows: Record<string, string>[] } {
  const clean = text.replace(/^﻿/, "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = clean.split("\n").filter((l) => l.trim());
  if (lines.length === 0) return { headers: [], rows: [] };
  const headers = splitLine(lines[0]).map((h) => h.replace(/^"|"$/g, ""));
  const rows = lines.slice(1).map((line) => {
    const values = splitLine(line).map((v) => v.replace(/^"|"$/g, ""));
    const row: Record<string, string> = {};
    headers.forEach((h, i) => { row[h] = values[i] ?? ""; });
    return row;
  });
  return { headers, rows };
}

function validateRow(row: Record<string, string>): string | null {
  if (!row.url?.trim()) return "Falta URL";
  try { new URL(row.url.trim()); } catch { return "URL inválida"; }
  if (!row.fuente?.trim()) return "Falta fuente";
  return null;
}

function rowToListing(row: Record<string, string>): ManualListingIn {
  const obj: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(row)) {
    if (!v?.trim()) continue;
    if (INT_FIELDS.has(k)) { const n = parseInt(v, 10); if (!isNaN(n)) obj[k] = n; }
    else if (BOOL_FIELDS.has(k)) { obj[k] = BOOL_TRUE.has(v.trim().toLowerCase()); }
    else { obj[k] = v.trim(); }
  }
  return obj as unknown as ManualListingIn;
}

function downloadTemplate() {
  const example = [
    "https://www.idealista.com/inmueble/12345/",
    "idealista", "Piso en el centro", "250000", "80", "3", "2",
    "Barcelona", "Eixample", "Barcelona", "buen_estado", "libre", "libre_cargas",
    "true", "false", "false", "C", "1200", "3500",
  ];
  const csv = CSV_HEADERS.join(",") + "\n" + example.join(",") + "\n";
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "plantilla_carga.csv"; a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type RowStatus = "nuevo" | "actualizado" | "rechazado";
interface PreviewRow {
  raw: Record<string, string>;
  listing: ManualListingIn | null;
  status: RowStatus;
  reason?: string;
}

// ---------------------------------------------------------------------------
// Manual form
// ---------------------------------------------------------------------------

const CONDITIONS: [string, string][] = [
  ["obra_nueva", "Nuevo"],
  ["listo_para_usar", "Listo para usar"],
  ["buen_estado", "Usado pero bien"],
  ["reforma_leve", "Reforma leve necesaria"],
  ["reforma_integral", "Reforma Integral / A reformar"],
  ["reforma_estructural", "Reforma estructural necesaria"],
];

const OCUPACION_OPTIONS: [string, string][] = [
  ["libre", "Libre / Desocupado"],
  ["ocupado", "Ocupado"],
  ["alquilado", "Alquilado"],
  ["nuda_propiedad", "Nuda propiedad"],
];

const SITUACION_LEGAL_OPTIONS: [string, string][] = [
  ["libre_cargas", "Libre de cargas"],
  ["con_hipoteca", "Con hipoteca"],
  ["en_construccion", "En construcción"],
  ["renta_antigua", "Renta antigua"],
  ["vpo", "VPO / Protección oficial"],
  ["subasta", "En subasta"],
  ["litigio", "En litigio"],
  ["herencia", "Herencia / En trámite"],
];

const CEE = ["A", "B", "C", "D", "E", "F", "G"];

const emptyForm = (): ManualListingIn => ({ url: "", fuente: "" });

function ManualForm() {
  const [form, setForm] = useState<ManualListingIn>(emptyForm());
  const [result, setResult] = useState<{ status: string } | null>(null);

  const fuentesQuery = useQuery({ queryKey: ["fuentes"], queryFn: () => fetchFuentes() });
  const fuentes = fuentesQuery.data ?? [];

  const mutation = useMutation({
    mutationFn: () => createManualListing(form),
    onSuccess: (data) => { setResult(data); setForm(emptyForm()); },
  });

  const set = (k: keyof ManualListingIn, v: unknown) =>
    setForm((f) => ({ ...f, [k]: v === "" ? undefined : v }));

  const isValid = Boolean(form.url && form.fuente);

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
      className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col gap-5"
    >
      {/* Identificación */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">URL <span className="text-red-500">*</span></label>
          <input
            required type="url" placeholder="https://..."
            value={form.url}
            onChange={(e) => set("url", e.target.value)}
            className="capitalize border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Fuente <span className="text-red-500">*</span></label>
          <select
            required
            value={form.fuente}
            onChange={(e) => set("fuente", e.target.value)}
            className="capitalize border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— seleccionar —</option>
            {fuentes.map((f) => <option key={f.id} value={f.id}>{f.nombre}</option>)}
          </select>
        </div>
      </div>

      {/* Título */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-gray-700">Título</label>
        <input
          placeholder="Piso en venta en..."
          value={form.titulo ?? ""}
          onChange={(e) => set("titulo", e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Precio y superficie */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {(
          [
            ["precio_venta", "Precio venta (€)", "250000"],
            ["metros_cuadrados", "M²", "80"],
            ["habitaciones", "Habitaciones", "3"],
            ["banos", "Baños", "2"],
          ] as [keyof ManualListingIn, string, string][]
        ).map(([k, label, ph]) => (
          <div key={k} className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700">{label}</label>
            <input
              type="number" min={0} placeholder={ph}
              value={form[k] as number ?? ""}
              onChange={(e) => set(k, e.target.value ? Number(e.target.value) : undefined)}
              className="capitalize border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        ))}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Planta</label>
          <input
            type="text" placeholder="ej: 3, Bajo, Ático"
            value={form.planta ?? ""}
            onChange={(e) => set("planta", e.target.value || undefined)}
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Localización */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(
          [
            ["municipio", "Municipio", "Barcelona"],
            ["barrio", "Barrio", "Eixample"],
            ["provincia", "Provincia", "Barcelona"],
          ] as [keyof ManualListingIn, string, string][]
        ).map(([k, label, ph]) => (
          <div key={k} className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700">{label}</label>
            <input
              placeholder={ph}
              value={form[k] as string ?? ""}
              onChange={(e) => set(k, e.target.value)}
              className="capitalize border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        ))}
      </div>

      {/* Referencia catastral */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-gray-700">
          Referencia catastral{" "}
          <span className="text-xs text-gray-400 font-normal">(opcional — si la conoces, el enriquecedor la usará directamente)</span>
        </label>
        <input
          placeholder="ej: 9872023VH5797S0001WX"
          value={form.referencia_catastral ?? ""}
          onChange={(e) => set("referencia_catastral", e.target.value || undefined)}
          className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Clasificación */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Condición</label>
          <select
            value={form.condition ?? ""}
            onChange={(e) => set("condition", e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— sin especificar —</option>
            {CONDITIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Ocupación</label>
          <select
            value={form.ocupacion ?? ""}
            onChange={(e) => set("ocupacion", e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— sin especificar —</option>
            {OCUPACION_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Situación legal</label>
          <select
            value={form.situacion_legal ?? ""}
            onChange={(e) => set("situacion_legal", e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— sin especificar —</option>
            {SITUACION_LEGAL_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      </div>

      {/* Características */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">CEE</label>
          <select
            value={form.certificado_energetico ?? ""}
            onChange={(e) => set("certificado_energetico", e.target.value)}
            className="capitalize border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">—</option>
            {CEE.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Alquiler est. (€/mes)</label>
          <input
            type="number" min={0} placeholder="1200"
            value={form.alquiler_estimado ?? ""}
            onChange={(e) => set("alquiler_estimado", e.target.value ? Number(e.target.value) : undefined)}
            className="capitalize border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Precio zona (€/m²)</label>
          <input
            type="number" min={0} placeholder="3500"
            value={form.precio_zona_m2 ?? ""}
            onChange={(e) => set("precio_zona_m2", e.target.value ? Number(e.target.value) : undefined)}
            className="capitalize border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Características del edificio */}
      <div className="flex flex-wrap gap-5">
        {(
          [
            ["ascensor", "Ascensor"],
            ["terraza", "Terraza"],
            ["garaje", "Garaje"],
            ["exterior", "Exterior"],
            ["portero", "Portero"],
            ["puerta_blindada", "Puerta blindada"],
            ["doble_acristalamiento", "Doble acristalamiento"],
            ["adaptado_movilidad", "Adaptado movilidad"],
          ] as [keyof ManualListingIn, string][]
        ).map(([k, label]) => (
          <label key={k} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input
              type="checkbox"
              checked={Boolean(form[k])}
              onChange={(e) => set(k, e.target.checked ? true : undefined)}
              className="w-4 h-4 accent-blue-600"
            />
            {label}
          </label>
        ))}
      </div>

      {/* Amenidades interiores */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Interior</p>
        <div className="flex flex-wrap gap-5">
          {(
            [
              ["balcon", "Balcón"],
              ["trastero", "Trastero"],
              ["armarios_empotrados", "Armarios empotrados"],
              ["aire_acondicionado", "Aire acondicionado"],
              ["calefaccion", "Calefacción"],
              ["cocina_equipada", "Cocina equipada"],
              ["amueblado", "Amueblado"],
            ] as [keyof ManualListingIn, string][]
          ).map(([k, label]) => (
            <label key={k} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={Boolean(form[k])}
                onChange={(e) => set(k, e.target.checked ? true : undefined)}
                className="w-4 h-4 accent-blue-600"
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      {/* Zonas comunitarias */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Zonas comunes</p>
        <div className="flex flex-wrap gap-5">
          {(
            [
              ["jardin", "Jardín"],
              ["piscina", "Piscina privada"],
              ["piscina_comunitaria", "Piscina comunitaria"],
              ["zonas_verdes_comunitarias", "Zonas verdes"],
              ["vigilancia", "Vigilancia"],
              ["garaje_incluido", "Garaje incluido en precio"],
            ] as [keyof ManualListingIn, string][]
          ).map(([k, label]) => (
            <label key={k} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={Boolean(form[k])}
                onChange={(e) => set(k, e.target.checked ? true : undefined)}
                className="w-4 h-4 accent-blue-600"
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      {result && (
        <div className={`px-4 py-3 rounded-lg text-sm font-medium ${
          result.status === "inserted"
            ? "bg-green-50 text-green-700 border border-green-200"
            : "bg-blue-50 text-blue-700 border border-blue-200"
        }`}>
          {result.status === "inserted" ? "✓ Anuncio añadido correctamente" : "✓ Anuncio actualizado correctamente"}
        </div>
      )}

      {mutation.isError && (
        <div className="px-4 py-3 rounded-lg text-sm bg-red-50 text-red-700 border border-red-200">
          Error al guardar. Verifica que la URL sea válida.
        </div>
      )}

      <button
        type="submit"
        disabled={!isValid || mutation.isPending}
        className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {mutation.isPending ? "Guardando…" : "Guardar anuncio"}
      </button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// CSV importer
// ---------------------------------------------------------------------------

const STATUS_STYLE: Record<RowStatus, string> = {
  nuevo:      "bg-green-100 text-green-700",
  actualizado: "bg-yellow-100 text-yellow-700",
  rechazado:  "bg-red-100 text-red-700",
};
const STATUS_LABEL: Record<RowStatus, string> = {
  nuevo: "Nuevo", actualizado: "Actualizado", rechazado: "Rechazado",
};

const COLUMN_DOCS: {
  key: string; tipo: string; req: boolean; desc: string; valores: string;
}[] = [
  { key: "url",                   tipo: "Texto",   req: true,  desc: "URL completa del anuncio",              valores: "https://... (obligatorio http/https)" },
  { key: "fuente",                tipo: "Texto",   req: true,  desc: "Portal de origen",                      valores: "idealista · fotocasa · habitaclia · pisos · manual" },
  { key: "titulo",                tipo: "Texto",   req: false, desc: "Título del anuncio",                    valores: "Cualquier texto" },
  { key: "precio_venta",          tipo: "Número",  req: false, desc: "Precio de venta en euros",              valores: "Entero sin puntos ni € — ej: 250000" },
  { key: "metros_cuadrados",      tipo: "Número",  req: false, desc: "Superficie en m²",                     valores: "Entero — ej: 80" },
  { key: "habitaciones",          tipo: "Número",  req: false, desc: "Número de habitaciones",                valores: "Entero — ej: 3" },
  { key: "banos",                 tipo: "Número",  req: false, desc: "Número de baños",                      valores: "Entero — ej: 2" },
  { key: "municipio",             tipo: "Texto",   req: false, desc: "Ciudad o municipio",                    valores: "Cualquier texto — ej: Barcelona" },
  { key: "barrio",                tipo: "Texto",   req: false, desc: "Barrio o distrito",                     valores: "Cualquier texto — ej: Eixample" },
  { key: "provincia",             tipo: "Texto",   req: false, desc: "Provincia",                             valores: "Cualquier texto — ej: Barcelona" },
  { key: "condition",              tipo: "Texto",   req: false, desc: "Condición física del inmueble",          valores: "obra_nueva · listo_para_usar · buen_estado · reforma_leve · reforma_integral · reforma_estructural" },
  { key: "ocupacion",              tipo: "Texto",   req: false, desc: "Quién ocupa el inmueble",                valores: "libre · ocupado · alquilado · nuda_propiedad" },
  { key: "situacion_legal",        tipo: "Texto",   req: false, desc: "Situación legal / cargas del título",   valores: "libre_cargas · con_hipoteca · en_construccion · renta_antigua · vpo · subasta · litigio · herencia" },
  { key: "ascensor",              tipo: "Booleano",req: false, desc: "Dispone de ascensor",                   valores: "true / false / 1 / 0 / si / no" },
  { key: "terraza",               tipo: "Booleano",req: false, desc: "Dispone de terraza",                    valores: "true / false / 1 / 0 / si / no" },
  { key: "garaje",                tipo: "Booleano",req: false, desc: "Incluye garaje",                        valores: "true / false / 1 / 0 / si / no" },
  { key: "certificado_energetico",tipo: "Texto",   req: false, desc: "Certificado de eficiencia energética",  valores: "A · B · C · D · E · F · G" },
  { key: "alquiler_estimado",     tipo: "Número",  req: false, desc: "Alquiler mensual estimado (€)",         valores: "Entero — ej: 1200" },
  { key: "precio_zona_m2",        tipo: "Número",  req: false, desc: "Precio medio de zona por m²",          valores: "Entero — ej: 3500" },
];

function CsvImporter() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [preview, setPreview] = useState<PreviewRow[] | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [importResult, setImportResult] = useState<BulkImportResult | null>(null);
  const [showInstructions, setShowInstructions] = useState(false);

  const validRows = (preview ?? []).filter((r) => r.status !== "rechazado");

  async function handleFile(file: File) {
    setPreview(null);
    setImportResult(null);
    const text = await file.text();
    const { headers, rows } = parseCSV(text);
    setCsvHeaders(headers);

    // Validate each row
    const pending: PreviewRow[] = rows.map((raw) => {
      const reason = validateRow(raw);
      if (reason) return { raw, listing: null, status: "rechazado", reason };
      return { raw, listing: rowToListing(raw), status: "nuevo" };
    });

    // Check existing URLs for valid rows
    const validUrls = pending
      .filter((r) => r.status !== "rechazado")
      .map((r) => r.raw.url.trim());

    if (validUrls.length > 0) {
      setIsChecking(true);
      try {
        const existing = await checkUrls(validUrls);
        pending.forEach((r) => {
          if (r.status !== "rechazado" && existing[r.raw.url.trim()]) {
            r.status = "actualizado";
          }
        });
      } catch {
        // If check fails, treat all valid as "nuevo"
      } finally {
        setIsChecking(false);
      }
    }

    setPreview(pending);
  }

  const importMutation = useMutation({
    mutationFn: () =>
      bulkImport(validRows.map((r) => r.listing!)),
    onSuccess: (data) => setImportResult(data),
  });

  const counts = preview
    ? {
        nuevo: preview.filter((r) => r.status === "nuevo").length,
        actualizado: preview.filter((r) => r.status === "actualizado").length,
        rechazado: preview.filter((r) => r.status === "rechazado").length,
      }
    : null;

  // Show columns present in CSV (in our defined order), always show status first
  const visibleCols = CSV_HEADERS.filter((h) => csvHeaders.includes(h));

  return (
    <div className="flex flex-col gap-5">
      {/* Download template — prominent button */}
      <button
        onClick={downloadTemplate}
        className="self-start flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
      >
        ↓ Descargar plantilla CSV
      </button>

      {/* Upload area */}
      <div
        className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const file = e.dataTransfer.files[0];
          if (file) handleFile(file);
        }}
      >
        <p className="text-gray-500 text-sm">
          Arrastra un CSV aquí o{" "}
          <span className="text-blue-600 font-medium">haz clic para seleccionar</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Formato: columnas separadas por coma, primera fila = cabeceras
        </p>
        <input
          ref={fileRef} type="file" accept=".csv,text/csv" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
      </div>

      {/* Instructions panel */}
      <div className="border border-blue-100 rounded-xl bg-blue-50 overflow-hidden">
        <button
          onClick={() => setShowInstructions((v) => !v)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-blue-800 hover:bg-blue-100 transition-colors"
        >
          <span>Instrucciones de importación</span>
          <span className="text-blue-400 text-xs">{showInstructions ? "▲ Ocultar" : "▼ Ver"}</span>
        </button>

        {showInstructions && (
          <div className="px-5 pb-5 flex flex-col gap-5 text-sm text-gray-700">

            {/* Tipo de archivo */}
            <div className="flex flex-col gap-1.5">
              <p className="font-semibold text-gray-800 text-xs uppercase tracking-wide">Tipo de archivo</p>
              <ul className="text-xs text-gray-600 flex flex-col gap-1 list-disc list-inside">
                <li>Formato <strong>CSV</strong> — valores separados por coma (<code className="bg-white px-1 rounded">,</code>)</li>
                <li>Codificación <strong>UTF-8</strong>. Desde Excel: <em>Guardar como → CSV UTF-8 (delimitado por comas)</em></li>
                <li>Primera fila: nombres de columna exactos (sin espacios extra ni mayúsculas)</li>
                <li>Solo se requieren las columnas <code className="bg-white px-1 rounded">url</code> y <code className="bg-white px-1 rounded">fuente</code>; el resto son opcionales</li>
              </ul>
            </div>

            {/* Columnas */}
            <div className="flex flex-col gap-2">
              <p className="font-semibold text-gray-800 text-xs uppercase tracking-wide">Columnas disponibles</p>
              <div className="overflow-x-auto rounded-lg border border-blue-100">
                <table className="w-full text-xs">
                  <thead className="bg-blue-100 text-blue-900">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold whitespace-nowrap">Columna</th>
                      <th className="px-3 py-2 text-left font-semibold">Tipo</th>
                      <th className="px-3 py-2 text-left font-semibold">Req.</th>
                      <th className="px-3 py-2 text-left font-semibold">Descripción</th>
                      <th className="px-3 py-2 text-left font-semibold">Valores aceptados</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-blue-50 bg-white">
                    {COLUMN_DOCS.map((col) => (
                      <tr key={col.key} className="hover:bg-blue-50">
                        <td className="px-3 py-2 font-mono text-blue-700 whitespace-nowrap">{col.key}</td>
                        <td className="px-3 py-2 text-gray-500 whitespace-nowrap">{col.tipo}</td>
                        <td className="px-3 py-2">
                          {col.req
                            ? <span className="text-red-600 font-bold">Sí</span>
                            : <span className="text-gray-400">No</span>}
                        </td>
                        <td className="px-3 py-2 text-gray-600">{col.desc}</td>
                        <td className="px-3 py-2 text-gray-500">{col.valores}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Caracteres prohibidos */}
            <div className="flex flex-col gap-1.5">
              <p className="font-semibold text-gray-800 text-xs uppercase tracking-wide">Caracteres y reglas importantes</p>
              <ul className="text-xs text-gray-600 flex flex-col gap-1 list-disc list-inside">
                <li>Si un campo contiene una <strong>coma</strong>, enciérralo entre comillas dobles: <code className="bg-white px-1 rounded">"Piso, con terraza"</code></li>
                <li>Si un campo contiene <strong>comillas dobles</strong>, duplícalas: <code className="bg-white px-1 rounded">"Piso ""reformado"""</code></li>
                <li>No se permiten <strong>saltos de línea</strong> dentro de un campo</li>
                <li>Los campos numéricos no deben incluir puntos de miles, comas decimales ni símbolos como <code className="bg-white px-1 rounded">€</code> o <code className="bg-white px-1 rounded">m²</code></li>
                <li>Los campos booleanos aceptan: <code className="bg-white px-1 rounded">true</code>, <code className="bg-white px-1 rounded">false</code>, <code className="bg-white px-1 rounded">1</code>, <code className="bg-white px-1 rounded">0</code>, <code className="bg-white px-1 rounded">si</code>, <code className="bg-white px-1 rounded">no</code></li>
              </ul>
            </div>

            {/* Ejemplo */}
            <div className="flex flex-col gap-1.5">
              <p className="font-semibold text-gray-800 text-xs uppercase tracking-wide">Ejemplo de fila válida</p>
              <pre className="text-xs bg-white border border-blue-100 rounded-lg px-4 py-3 overflow-x-auto text-gray-600 leading-relaxed whitespace-pre">
{`url,fuente,titulo,precio_venta,metros_cuadrados,habitaciones,banos,municipio,barrio,condition,ocupacion,situacion_legal,ascensor,terraza,garaje,certificado_energetico,alquiler_estimado
https://www.idealista.com/inmueble/12345/,idealista,Piso en Eixample reformado,250000,80,3,2,Barcelona,Eixample,buen_estado,libre,libre_cargas,true,false,false,C,1200`}
              </pre>
            </div>

          </div>
        )}
      </div>

      {isChecking && (
        <p className="text-sm text-gray-400">Verificando URLs en base de datos…</p>
      )}

      {/* Summary */}
      {counts && (
        <div className="flex gap-3 flex-wrap">
          {(["nuevo", "actualizado", "rechazado"] as RowStatus[]).map((s) => (
            <span key={s} className={`text-xs font-medium px-3 py-1.5 rounded-full ${STATUS_STYLE[s]}`}>
              {STATUS_LABEL[s]}: {counts[s]}
            </span>
          ))}
          <span className="text-xs text-gray-400 self-center">
            Total: {preview!.length} filas
          </span>
        </div>
      )}

      {/* Preview table */}
      {preview && preview.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
          <table className="text-xs min-w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-3 py-2.5 text-left font-semibold text-gray-600 sticky left-0 bg-gray-50 z-10">
                  Estado
                </th>
                {visibleCols.map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left font-semibold text-gray-600 whitespace-nowrap">
                    {HEADER_LABELS[h] ?? h}
                  </th>
                ))}
                <th className="px-3 py-2.5 text-left font-semibold text-gray-500">Motivo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {preview.map((row, i) => (
                <tr key={i} className={row.status === "rechazado" ? "bg-red-50" : "bg-white hover:bg-gray-50"}>
                  <td className="px-3 py-2 sticky left-0 bg-inherit z-10">
                    <span className={`px-2 py-0.5 rounded-full font-medium ${STATUS_STYLE[row.status]}`}>
                      {STATUS_LABEL[row.status]}
                    </span>
                  </td>
                  {visibleCols.map((h) => (
                    <td key={h} className="px-3 py-2 text-gray-700 whitespace-nowrap max-w-[200px] truncate">
                      {h === "url" ? (
                        <a
                          href={row.raw[h]} target="_blank" rel="noreferrer"
                          className="text-blue-500 hover:underline truncate block max-w-[200px]"
                          title={row.raw[h]}
                        >
                          {row.raw[h]}
                        </a>
                      ) : (
                        <span title={row.raw[h]}>{row.raw[h] || "—"}</span>
                      )}
                    </td>
                  ))}
                  <td className="px-3 py-2 text-red-500 whitespace-nowrap">
                    {row.reason ?? ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Import button */}
      {preview && validRows.length > 0 && !importResult && (
        <button
          onClick={() => importMutation.mutate()}
          disabled={importMutation.isPending}
          className="self-start px-6 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {importMutation.isPending
            ? "Importando…"
            : `Importar ${validRows.length} registro${validRows.length !== 1 ? "s" : ""}`}
        </button>
      )}

      {/* Import result */}
      {importResult && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-5 flex flex-col gap-2">
          <p className="font-medium text-green-800">Importación completada</p>
          <div className="flex gap-4 text-sm">
            <span className="text-green-700">✓ {importResult.inserted} nuevos</span>
            <span className="text-yellow-700">↻ {importResult.updated} actualizados</span>
            {importResult.errors > 0 && (
              <span className="text-red-600">✗ {importResult.errors} errores</span>
            )}
          </div>
          {importResult.error_details.length > 0 && (
            <div className="mt-2 flex flex-col gap-1">
              {importResult.error_details.map((e, i) => (
                <p key={i} className="text-xs text-red-600 truncate">
                  {e.url}: {e.error}
                </p>
              ))}
            </div>
          )}
          <button
            onClick={() => { setPreview(null); setImportResult(null); setCsvHeaders([]); if (fileRef.current) fileRef.current.value = ""; }}
            className="self-start text-xs text-blue-600 hover:underline mt-1"
          >
            ← Nueva importación
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type Tab = "form" | "csv";

export default function Carga() {
  const [tab, setTab] = useState<Tab>("form");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Carga manual</h1>
        <p className="text-sm text-gray-400 mt-1">
          Añade oportunidades manualmente o importa desde CSV
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {(
          [
            ["form", "Formulario manual"],
            ["csv", "Importar CSV"],
          ] as [Tab, string][]
        ).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t
                ? "bg-white text-gray-800 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "form" ? <ManualForm /> : <CsvImporter />}
    </div>
  );
}
