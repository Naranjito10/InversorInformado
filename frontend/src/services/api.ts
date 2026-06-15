import axios from "axios";
import type { Listing, Stats, Zone, SearchRequest, SearchResponse } from "../types";

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const login = async (
  email: string,
  password: string
): Promise<{ access_token: string; token_type: string }> => {
  const { data } = await axios.post("/api/auth/login", { email, password });
  return data;
};

export const logout = (): void => {
  localStorage.removeItem("token");
  window.location.href = "/login";
};

export interface ListingFilters {
  municipio?: string;
  barrio?: string;
  fuente?: string;
  score_label?: string;
  score_min?: number;
  precio_min?: number;
  precio_max?: number;
  solo_activos?: boolean;
  limit?: number;
  q?: string;
}

export interface ZonaOption {
  tipo: "municipio" | "barrio";
  valor: string;
  label: string;
  municipio?: string;
}

export const fetchListingZonas = async (): Promise<ZonaOption[]> => {
  const { data } = await api.get<ZonaOption[]>("/listings/zonas");
  return data;
};

export const fetchListings = async (filters: ListingFilters = {}): Promise<Listing[]> => {
  const { data } = await api.get<Listing[]>("/listings", { params: filters });
  return data;
};

export const fetchStats = async (): Promise<Stats> => {
  const { data } = await api.get<Stats>("/listings/stats");
  return data;
};

export const fetchZones = async (): Promise<Zone[]> => {
  const { data } = await api.get<Zone[]>("/zones");
  return data;
};

export const runScraper = async (): Promise<{ status: string; message: string }> => {
  const { data } = await api.post("/scraper/run");
  return data;
};

export const runSearch = async (req: SearchRequest): Promise<SearchResponse> => {
  const { data } = await api.post<SearchResponse>("/scraper/search", req);
  return data;
};

export interface PortalTestResult {
  portal: string;
  url?: string;
  status: "ok" | "blocked" | "error";
  detail: string;
  response_ms?: number;
  listings_found?: number;
}

export interface LogEntry {
  ts?: string;
  level?: string;
  logger?: string;
  msg?: string;
  [key: string]: unknown;
}

export interface LogsResponse {
  lines: LogEntry[];
  total: number;
  error?: string;
}

export const testPortal = async (portal: string): Promise<PortalTestResult> => {
  const { data } = await api.post<PortalTestResult>(`/monitor/test/${portal}`);
  return data;
};

export const fetchLogs = async (lines = 50): Promise<LogsResponse> => {
  const { data } = await api.get<LogsResponse>("/monitor/logs", { params: { lines } });
  return data;
};

export interface OriginalListingInfo {
  titulo?: string;
  precio_venta?: number;
  metros_cuadrados?: number;
  habitaciones?: number;
  barrio?: string;
  municipio?: string;
  primera_deteccion?: string;
  url: string;
}

export interface PendingListing {
  id: string;
  url: string;
  fuente: string;
  titulo?: string;
  precio_venta?: number;
  metros_cuadrados?: number;
  habitaciones?: number;
  barrio?: string;
  municipio?: string;
  status: string;
  duplicate_candidate_of?: string;
  primera_deteccion?: string;
  original_info?: OriginalListingInfo;
}

export const fetchPendingReview = async (): Promise<PendingListing[]> => {
  const { data } = await api.get<PendingListing[]>("/listings/pending-review");
  return data;
};

export const approveListing = async (id: string): Promise<void> => {
  await api.post(`/listings/${id}/approve`);
};

export const rejectListing = async (id: string): Promise<void> => {
  await api.post(`/listings/${id}/reject`);
};

export const keepNewListing = async (id: string): Promise<void> => {
  await api.post(`/listings/${id}/keep-new`);
};

export interface ManualListingIn {
  url: string;
  fuente: string;
  titulo?: string;
  precio_venta?: number;
  metros_cuadrados?: number;
  habitaciones?: number;
  banos?: number;
  municipio?: string;
  barrio?: string;
  provincia?: string;
  condition?: string;
  ocupacion?: string;
  situacion_legal?: string;
  ascensor?: boolean;
  terraza?: boolean;
  garaje?: boolean;
  certificado_energetico?: string;
  alquiler_estimado?: number;
  precio_zona_m2?: number;
  planta?: string;
  // Amenidades interiores
  balcon?: boolean;
  trastero?: boolean;
  armarios_empotrados?: boolean;
  aire_acondicionado?: boolean;
  calefaccion?: boolean;
  calefaccion_tipo?: string;
  cocina_equipada?: boolean;
  amueblado?: boolean;
  // Edificio
  exterior?: boolean;
  orientacion?: string;
  portero?: boolean;
  puerta_blindada?: boolean;
  doble_acristalamiento?: boolean;
  adaptado_movilidad?: boolean;
  // Zonas exteriores / comunidad
  jardin?: boolean;
  piscina?: boolean;
  piscina_comunitaria?: boolean;
  zonas_verdes_comunitarias?: boolean;
  vigilancia?: boolean;
  // Garaje
  garaje_incluido?: boolean;
  num_plazas_garaje?: number;
}

export interface BulkImportResult {
  inserted: number;
  updated: number;
  errors: number;
  error_details: { url: string; error: string }[];
}

export const createManualListing = async (
  data: ManualListingIn
): Promise<{ status: string; ok: boolean }> => {
  const { data: result } = await api.post("/listings/manual", data);
  return result;
};

export const checkUrls = async (
  urls: string[]
): Promise<Record<string, boolean>> => {
  const { data } = await api.post<Record<string, boolean>>("/listings/check-urls", { urls });
  return data;
};

export const bulkImport = async (
  listings: ManualListingIn[]
): Promise<BulkImportResult> => {
  const { data } = await api.post<BulkImportResult>("/listings/bulk", { listings });
  return data;
};

export interface Fuente {
  id: string;
  nombre: string;
  activo: boolean;
  test_url?: string;
  created_at?: string;
}

export const fetchFuentes = async (soloActivos = false): Promise<Fuente[]> => {
  const { data } = await api.get<Fuente[]>("/fuentes", {
    params: soloActivos ? { solo_activos: true } : {},
  });
  return data;
};

export const createFuente = async (
  id: string,
  nombre: string,
  test_url?: string
): Promise<Fuente> => {
  const { data } = await api.post<Fuente>("/fuentes", { id, nombre, test_url });
  return data;
};

export const toggleFuente = async (id: string, activo: boolean): Promise<Fuente> => {
  const { data } = await api.patch<Fuente>(`/fuentes/${id}/toggle`, { activo });
  return data;
};

export const updateFuente = async (
  id: string,
  nombre: string,
  test_url?: string
): Promise<Fuente> => {
  const { data } = await api.put<Fuente>(`/fuentes/${id}`, { nombre, test_url: test_url || null });
  return data;
};

export const deleteFuente = async (id: string): Promise<void> => {
  await api.delete(`/fuentes/${id}`);
};

export const exportExcel = async (filters: ListingFilters = {}): Promise<void> => {
  const response = await api.get("/export/excel", {
    params: filters,
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", "oportunidades.xlsx");
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// ── Reports ──────────────────────────────────────────────────────────────────

export interface ReportCreateIn {
  type?: string;
  title: string;
  property_id?: string | null;
  data: import("../types").ReportData;
}

export const fetchReports = async (): Promise<import("../types").Report[]> => {
  const { data } = await api.get<import("../types").Report[]>("/reports");
  return data;
};

export const createReport = async (
  payload: ReportCreateIn
): Promise<import("../types").Report> => {
  const { data } = await api.post<import("../types").Report>("/reports", payload);
  return data;
};

export const fetchReport = async (id: string): Promise<import("../types").Report> => {
  const { data } = await api.get<import("../types").Report>(`/reports/${id}`);
  return data;
};

export const getReportHtmlUrl = (id: string): string => `/api/reports/${id}/html`;
export const getReportPdfUrl = (id: string): string => `/api/reports/${id}/pdf`;

export const fetchReportHtmlBlob = async (id: string): Promise<string> => {
  const resp = await api.get(`/reports/${id}/html`, { responseType: "blob" });
  return URL.createObjectURL(resp.data);
};

export const downloadReportPdf = async (id: string, title: string): Promise<void> => {
  const resp = await api.get(`/reports/${id}/pdf`, { responseType: "blob" });
  const url = URL.createObjectURL(resp.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title.toLowerCase().replace(/\s+/g, "-")}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
};

export interface AIEstimateRequest {
  municipio: string;
  barrio: string;
  precio: number;
  metros: number;
  habitaciones: number;
  condition?: string;
}

export const aiEstimateMarket = async (
  req: AIEstimateRequest
): Promise<import("../types").ReportMarket> => {
  const { data } = await api.post<import("../types").ReportMarket>("/reports/ai-estimate", req);
  return data;
};

// ── Telegram ─────────────────────────────────────────────────────────────────

export const fetchTelegramLog = async (): Promise<import("../types").TelegramLogEntry[]> => {
  const { data } = await api.get<import("../types").TelegramLogEntry[]>("/telegram/log");
  return data;
};

export const publishReportToTelegram = async (
  reportId: string
): Promise<{ status: string; preview: string }> => {
  const { data } = await api.post(`/telegram/publish-report/${reportId}`);
  return data;
};

export const generateWeeklyReport = async (): Promise<{
  status: string;
  properties_featured?: number;
  preview?: string;
}> => {
  const { data } = await api.post("/telegram/generate-weekly");
  return data;
};

export interface ScraperStatus {
  running: boolean;
  done: boolean;
  event: string | null;
  message: string | null;
  portal: string | null;
  new: number;
  updated: number;
  errors: number;
  queued: number;
  started_at: string | null;
  finished_at: string | null;
}

export const fetchScraperStatus = async (): Promise<ScraperStatus> => {
  const { data } = await api.get<ScraperStatus>("/scraper/status");
  return data;
};

export const dismissScraperStatus = async (): Promise<void> => {
  await api.post("/scraper/status/dismiss");
};

export const publishTelegram = async (req: {
  type: string;
  title: string;
  body: string;
  zone?: string;
}): Promise<{ status: string; channel_id: string }> => {
  const { data } = await api.post("/telegram/publish", req);
  return data;
};