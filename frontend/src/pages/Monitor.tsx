import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { testPortal, fetchLogs } from "../services/api";
import type { PortalTestResult, LogEntry } from "../services/api";

const PORTALES = ["habitaclia", "pisos", "idealista", "fotocasa", "casaradar"];

const PORTAL_LABEL: Record<string, string> = {
  habitaclia: "Habitaclia",
  pisos: "Pisos.com",
  idealista: "Idealista",
  fotocasa: "Fotocasa",
  casaradar: "Casaradar",
};

const STATUS_STYLE: Record<string, string> = {
  ok:      "bg-green-100 text-green-800",
  blocked: "bg-yellow-100 text-yellow-800",
  error:   "bg-red-100 text-red-700",
};

const STATUS_ICON: Record<string, string> = {
  ok:      "✅",
  blocked: "⚠️",
  error:   "❌",
};

const LEVEL_STYLE: Record<string, string> = {
  ERROR:   "text-red-600 font-semibold",
  WARNING: "text-yellow-600",
  INFO:    "text-gray-500",
  DEBUG:   "text-gray-300",
  RAW:     "text-gray-400 italic",
};

function formatTs(ts?: string): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString("es-ES", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function PortalCard({ portal }: { portal: string }) {
  const [result, setResult] = useState<PortalTestResult | null>(null);

  const mutation = useMutation({
    mutationFn: () => testPortal(portal),
    onSuccess: (data) => setResult(data),
  });

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-gray-800 capitalize">
          {PORTAL_LABEL[portal] ?? portal}
        </span>
        {result && (
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLE[result.status]}`}>
            {STATUS_ICON[result.status]} {result.status.toUpperCase()}
          </span>
        )}
      </div>

      {result ? (
        <div className="flex flex-col gap-1 text-sm text-gray-600">
          <p>{result.detail}</p>
          {result.response_ms != null && (
            <p className="text-xs text-gray-400">{result.response_ms} ms</p>
          )}
          {result.url && (
            <a
              href={result.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-blue-500 hover:underline truncate"
            >
              {result.url}
            </a>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-400">Sin probar</p>
      )}

      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="mt-auto w-full py-2 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {mutation.isPending ? "Probando…" : "Probar conexión"}
      </button>
    </div>
  );
}

function LogRow({ entry }: { entry: LogEntry }) {
  const level = (entry.level as string) ?? "INFO";
  const msg = (entry.msg as string) ?? (entry.raw as string) ?? "";
  const logger = (entry.logger as string) ?? "";

  // Extras: todo lo que no son campos base
  const extras = Object.entries(entry).filter(
    ([k]) => !["ts", "level", "logger", "msg", "raw"].includes(k)
  );

  return (
    <div className="flex gap-3 py-2 border-b border-gray-50 text-xs font-mono">
      <span className="text-gray-300 shrink-0 w-20">{formatTs(entry.ts as string)}</span>
      <span className={`shrink-0 w-16 ${LEVEL_STYLE[level] ?? LEVEL_STYLE.INFO}`}>
        {level}
      </span>
      <span className="text-blue-400 shrink-0 w-28 truncate">{logger}</span>
      <span className="text-gray-700 flex-1 break-all">
        {msg}
        {extras.length > 0 && (
          <span className="text-gray-400 ml-2">
            {extras.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(" ")}
          </span>
        )}
      </span>
    </div>
  );
}

export default function Monitor() {
  const [logLines, setLogLines] = useState(50);

  const logsQuery = useQuery({
    queryKey: ["logs", logLines],
    queryFn: () => fetchLogs(logLines),
    refetchInterval: 30_000,
  });

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Monitor</h1>
        <p className="text-sm text-gray-400 mt-1">
          Estado de portales y logs del sistema
        </p>
      </div>

      {/* Portales */}
      <section className="flex flex-col gap-3">
        <h2 className="text-base font-semibold text-gray-700">Estado de portales</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {PORTALES.map((p) => (
            <PortalCard key={p} portal={p} />
          ))}
        </div>
      </section>

      {/* Logs */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-base font-semibold text-gray-700">Logs del scraper</h2>
            {logsQuery.data && (
              <span className="text-xs text-gray-400">
                {logsQuery.data.total} entradas en total
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <select
              value={logLines}
              onChange={(e) => setLogLines(Number(e.target.value))}
              className="text-xs border border-gray-300 rounded-lg px-2 py-1.5 text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {[50, 100, 200, 500].map((n) => (
                <option key={n} value={n}>Últimas {n}</option>
              ))}
            </select>
            <button
              onClick={() => logsQuery.refetch()}
              className="text-xs px-3 py-1.5 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
            >
              ↻ Actualizar
            </button>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          {logsQuery.isLoading ? (
            <p className="text-sm text-gray-400 text-center py-10">Cargando logs…</p>
          ) : logsQuery.data?.error ? (
            <p className="text-sm text-red-500 text-center py-10">{logsQuery.data.error}</p>
          ) : !logsQuery.data?.lines.length ? (
            <p className="text-sm text-gray-400 text-center py-10">
              Sin logs todavía. Lanza un ciclo de scraping primero.
            </p>
          ) : (
            <div className="px-4 py-2 max-h-[500px] overflow-y-auto">
              {logsQuery.data.lines.map((entry, i) => (
                <LogRow key={i} entry={entry} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
