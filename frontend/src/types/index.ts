export interface Listing {
  id?: string;
  url: string;
  fuente: string;
  titulo?: string;
  precio_venta?: number;
  metros_cuadrados?: number;
  habitaciones?: number;
  banos?: number;
  planta?: string;
  tipo_propiedad?: string;
  barrio?: string;
  municipio?: string;
  estado?: string;
  ascensor?: boolean;
  terraza?: boolean;
  garaje?: boolean;
  precio_m2?: number;
  rentabilidad_bruta?: number;
  score?: number;
  score_label?: string;
  bajada_precio?: boolean;
  dias_en_mercado?: number;
  activo?: boolean;
  cee?: string;
  primera_deteccion?: string;
  ultima_actualizacion?: string;
}

export interface Stats {
  total_activos: number;
  nuevos_esta_semana: number;
  score_medio: number;
  bajadas_precio: number;
  por_fuente: Record<string, number>;
  por_label: Record<string, number>;
}

export interface Zone {
  key: string;
  label: string;
  portales_disponibles: string[];
}

export interface SearchRequest {
  zona: string;
  precio_min?: number;
  precio_max?: number;
  portales: string[];
  max_pages: number;
}

export interface SearchResponse {
  status: string;
  zona: string;
  portales: string[];
  targets: number;
  search_urls: string[];
}

export interface ReportProperty {
  direccion: string;
  municipio: string;
  barrio: string;
  precio: number;
  metros: number;
  habitaciones: number;
  banos: number;
  estado: string;
  url: string;
  cee?: string;
}

export interface ReportMarket {
  precio_m2_zona_min: number;
  precio_m2_zona_medio: number;
  precio_m2_zona_max: number;
  alquiler_estimado_mes: number;
  rentabilidad_bruta: number;
  rentabilidad_neta: number;
  rentabilidad_bruta_media_zona: number;
  rentabilidad_neta_media_zona: number;
  demanda_alquiler: "muy_alta" | "alta" | "media" | "baja";
  dias_hasta_alquiler: number;
  ai_estimated?: boolean;
  alquiler_vs_media_pct?: number;
  percentil_precio?: number;
  percentil_rentabilidad?: number;
  percentil_vecindario?: number;
}

export interface ReportBuilding {
  anyo_construccion?: number;
  ite_resultado?: string;
  ite_fecha?: string;
  humedades?: boolean;
  ascensor?: boolean;
  electrica?: string;
  fondo_reserva?: number;
  fondo_reserva_estado?: string;
  alerta_reformas?: string;
}

export interface ReportScores {
  global: number;
  global_grade: string;
  precio: number;
  precio_grade: string;
  rentabilidad: number;
  rentabilidad_grade: string;
  edificio: number;
  edificio_grade: string;
  vecindario: number;
  vecindario_grade: string;
  resumen: string;
  percentil_precio?: number;
  percentil_rentabilidad?: number;
  percentil_vecindario?: number;
}

export interface ReportAmenities {
  transporte?: number;
  colegios?: number;
  salud?: number;
  comercios?: number;
  zonas_verdes?: number;
  seguridad?: number;
  ambiente?: number;
  aparcamiento?: number;
  descripcion_cercano?: string;
}

export interface ReportData {
  property: ReportProperty;
  market: ReportMarket;
  building: ReportBuilding;
  scores: ReportScores;
  amenities: ReportAmenities;
  verdict: string;
}

export interface Report {
  id: string;
  type: string;
  title: string;
  property_id: string | null;
  data: ReportData;
  created_at: string;
}

export interface TelegramLogEntry {
  id: string;
  type: "manual" | "auto" | "from_report";
  content: string;
  report_id: string | null;
  status: "sent" | "failed";
  sent_at: string;
}