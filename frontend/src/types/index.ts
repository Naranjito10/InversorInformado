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