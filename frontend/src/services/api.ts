import axios from "axios";
import type { Listing, Stats, Zone, SearchRequest, SearchResponse } from "../types";

const api = axios.create({ baseURL: "/api" });

export interface ListingFilters {
  municipio?: string;
  fuente?: string;
  score_label?: string;
  score_min?: number;
  precio_min?: number;
  precio_max?: number;
  solo_activos?: boolean;
  limit?: number;
}

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
  pending_review: boolean;
  duplicate_candidate_of?: string;
  primera_deteccion?: string;
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
  estado?: string;
  ascensor?: boolean;
  terraza?: boolean;
  garaje?: boolean;
  certificado_energetico?: string;
  alquiler_estimado?: number;
  precio_zona_m2?: number;
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

export const exportExcel = (filters: ListingFilters = {}): void => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.append(k, String(v));
  });
  window.open(`/api/export/excel?${params.toString()}`, "_blank");
};