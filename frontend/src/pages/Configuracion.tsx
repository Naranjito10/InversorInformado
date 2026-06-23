import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchConfig, updateConfig, runEnricher } from "../services/api";
import type { ConfigEntry } from "../services/api";

function formatDate(ts?: string | null): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

function ConfigRow({ entry }: { entry: ConfigEntry }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(entry.value);

  const mutation = useMutation({
    mutationFn: () => updateConfig(entry.key, draft),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["config"] });
      setEditing(false);
    },
  });

  const handleCancel = () => {
    setDraft(entry.value);
    setEditing(false);
  };

  return (
    <tr className="border-t border-gray-100">
      <td className="px-6 py-3 align-top">
        <code className="text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded font-mono">
          {entry.key}
        </code>
      </td>
      <td className="py-3 pr-4 align-top w-32">
        {editing ? (
          <input
            type="text"
            value={draft}
            autoFocus
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") mutation.mutate();
              if (e.key === "Escape") handleCancel();
            }}
            className="w-full border border-blue-400 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        ) : (
          <span className="text-sm font-semibold text-gray-800">{entry.value}</span>
        )}
      </td>
      <td className="py-3 pr-4 align-top text-sm text-gray-500">
        {entry.description ?? "—"}
      </td>
      <td className="py-3 pr-4 align-top text-xs text-gray-400 whitespace-nowrap">
        {formatDate(entry.updated_at)}
      </td>
      <td className="py-3 px-6 align-top">
        {editing ? (
          <div className="flex gap-2">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {mutation.isPending ? "…" : "Guardar"}
            </button>
            <button
              onClick={handleCancel}
              className="px-3 py-1 text-xs border border-gray-300 text-gray-600 rounded hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
          </div>
        ) : (
          <button
            onClick={() => { setDraft(entry.value); setEditing(true); }}
            className="px-3 py-1 text-xs border border-gray-300 text-gray-600 rounded hover:bg-gray-50 transition-colors"
          >
            Editar
          </button>
        )}
      </td>
    </tr>
  );
}

export default function Configuracion() {
  const { data: entries = [], isLoading, isError } = useQuery({
    queryKey: ["config"],
    queryFn: fetchConfig,
    staleTime: 30_000,
  });

  const enrichMutation = useMutation({
    mutationFn: runEnricher,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Configuración del sistema</h1>
          <p className="text-sm text-gray-400 mt-1">
            Parámetros de enriquecimiento, revisión y umbrales. Haz clic en Editar para modificar un valor.
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <button
            onClick={() => enrichMutation.mutate()}
            disabled={enrichMutation.isPending}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {enrichMutation.isPending ? "Encolando…" : "Ejecutar enriquecimiento"}
          </button>
          {enrichMutation.isSuccess && (
            <p className="text-xs text-green-600">Encolado — revisa los logs en Monitoreo</p>
          )}
          {enrichMutation.isError && (
            <p className="text-xs text-red-500">Error al encolar. Revisa la API.</p>
          )}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <p className="text-sm text-gray-400 p-6">Cargando configuración…</p>
        ) : isError ? (
          <p className="text-sm text-red-500 p-6">Error al cargar la configuración.</p>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Clave</th>
                <th className="py-3 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">Valor</th>
                <th className="py-3 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">Descripción</th>
                <th className="py-3 pr-4 text-xs font-semibold text-gray-500 uppercase tracking-wide">Actualizado</th>
                <th className="py-3 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wide"></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <ConfigRow key={entry.key} entry={entry} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
