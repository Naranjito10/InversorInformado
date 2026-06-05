import { useState, useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchScraperStatus, dismissScraperStatus } from "../services/api";
import type { ScraperStatus } from "../services/api";

const EVENT_LABELS: Record<string, string> = {
  started:                      "Iniciando búsqueda...",
  target_start:                 "Conectando con portal...",
  listing_inserted:             "Piso guardado",
  listing_updated:              "Piso actualizado",
  duplicate_candidate_detected: "Posible duplicado detectado",
  cycle_done:                   "Búsqueda completada",
};

export default function ScraperToast() {
  const qc = useQueryClient();
  const [dismissed, setDismissed] = useState(false);
  const [visible, setVisible] = useState(false);
  const prevRunning = useRef(false);

  const { data: status } = useQuery<ScraperStatus>({
    queryKey: ["scraper-status"],
    queryFn: fetchScraperStatus,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.running) return 2_000;
      if (data?.done && !dismissed) return 10_000;
      return 15_000;
    },
    staleTime: 0,
  });

  useEffect(() => {
    if (!status) return;
    if (status.running && !prevRunning.current) {
      setDismissed(false);
      setVisible(true);
    }
    if (!status.running && !status.done) {
      // idle state — hide if dismissed
    }
    prevRunning.current = status.running;

    if (status.running || status.done) {
      setVisible(true);
    }
  }, [status]);

  const handleDismiss = async () => {
    await dismissScraperStatus();
    setDismissed(true);
    setVisible(false);
    qc.invalidateQueries({ queryKey: ["listings"] });
    qc.invalidateQueries({ queryKey: ["scraper-status"] });
  };

  if (!status || (!status.running && !status.done) || dismissed || !visible) {
    return null;
  }

  const isDone = status.done && !status.running;
  const label = isDone
    ? "Búsqueda completada"
    : (status.message ?? EVENT_LABELS[status.event ?? ""] ?? "Scraper ejecutándose...");

  return (
    <div
      className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-4 duration-300"
      style={{ animation: "slideUp 0.3s ease-out" }}
    >
      <style>{`
        @keyframes slideUp {
          from { transform: translateY(16px); opacity: 0; }
          to   { transform: translateY(0);    opacity: 1; }
        }
      `}</style>

      <div className="bg-white border border-green-200 rounded-2xl shadow-xl w-72 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 pt-3.5 pb-2 bg-green-50">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-6 h-6 rounded-full bg-green-200">
              {isDone
                ? <svg className="h-3.5 w-3.5 text-green-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                : <svg className="animate-spin h-3.5 w-3.5 text-green-700" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" /></svg>
              }
            </div>
            <span className="text-xs font-semibold uppercase tracking-wider text-green-700">
              {isDone ? "Completado" : status.portal ? status.portal : "Scraper activo"}
            </span>
          </div>
          {isDone && (
            <button
              onClick={handleDismiss}
              className="text-green-400 hover:text-green-700 transition-colors text-lg leading-none"
            >
              ×
            </button>
          )}
        </div>

        {/* Message */}
        <div className="px-4 py-3">
          <p className="text-sm font-medium text-gray-800 leading-snug">{label}</p>
        </div>

        {/* Stats bar */}
        {(status.new > 0 || status.updated > 0 || isDone) && (
          <div className="bg-green-50 border-t border-green-100 px-4 py-2.5 flex items-center gap-4 text-xs text-gray-500">
            <span>
              <span className="font-bold text-green-700">{status.new}</span> nuevos
            </span>
            <span>
              <span className="font-bold text-gray-700">{status.updated}</span> actualizados
            </span>
            {status.errors > 0 && (
              <span>
                <span className="font-bold text-red-500">{status.errors}</span> errores
              </span>
            )}
          </div>
        )}

        {/* Progress pulse bar (only while running) */}
        {!isDone && (
          <div className="h-1 bg-green-100 overflow-hidden">
            <div
              className="h-full bg-green-400 rounded-full"
              style={{ animation: "pulse-bar 2s ease-in-out infinite", width: "40%" }}
            />
          </div>
        )}
        <style>{`
          @keyframes pulse-bar {
            0%   { transform: translateX(-100%); }
            100% { transform: translateX(350%); }
          }
        `}</style>
      </div>
    </div>
  );
}
