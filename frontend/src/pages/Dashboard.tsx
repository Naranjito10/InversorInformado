import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchListings, fetchStats, runScraper, exportExcel } from "../services/api";
import type { ListingFilters } from "../services/api";
import StatsCards from "../components/StatsCards";
import Filters from "../components/Filters";
import ListingsTable from "../components/ListingsTable";

export default function Dashboard() {
  const [filters, setFilters] = useState<ListingFilters>({});

  const statsQuery = useQuery({ queryKey: ["stats"], queryFn: fetchStats });
  const listingsQuery = useQuery({
    queryKey: ["listings", filters],
    queryFn: () => fetchListings(filters),
  });

  const scraperMutation = useMutation({
    mutationFn: runScraper,
    onSuccess: () => {
      setTimeout(() => {
        statsQuery.refetch();
        listingsQuery.refetch();
      }, 3000);
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          <p className="text-sm text-gray-400">Oportunidades de inversión inmobiliaria</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => exportExcel(filters)}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Exportar Excel
          </button>
          <button
            onClick={() => scraperMutation.mutate()}
            disabled={scraperMutation.isPending}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {scraperMutation.isPending ? "Lanzando..." : "Lanzar scraper"}
          </button>
        </div>
      </div>

      {scraperMutation.isSuccess && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
          Ciclo de scraping iniciado. Los datos se actualizarán en breve.
        </div>
      )}

      {statsQuery.data && <StatsCards stats={statsQuery.data} />}

      <Filters filters={filters} onChange={setFilters} />

      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          {listingsQuery.data
            ? `${listingsQuery.data.length} anuncios`
            : "Cargando..."}
        </p>
      </div>

      <ListingsTable
        listings={listingsQuery.data ?? []}
        isLoading={listingsQuery.isLoading}
      />
    </div>
  );
}