import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchTelegramLog, publishTelegram, generateWeeklyReport } from "../services/api";
import type { TelegramLogEntry } from "../types";

const TYPE_LABEL: Record<string, string> = {
  manual: "Manual",
  auto: "Auto",
  from_report: "Informe",
};

const TYPE_COLOR: Record<string, string> = {
  manual: "bg-blue-100 text-blue-700",
  auto: "bg-purple-100 text-purple-700",
  from_report: "bg-green-100 text-green-700",
};

export default function Comunicaciones() {
  const [form, setForm] = useState({ type: "oportunidades", title: "", body: "", zone: "" });
  const [preview, setPreview] = useState(false);

  const { data: log = [], refetch: refetchLog } = useQuery<TelegramLogEntry[]>({
    queryKey: ["telegram-log"],
    queryFn: fetchTelegramLog,
    refetchInterval: 30_000,
  });

  const publishMutation = useMutation({
    mutationFn: () =>
      publishTelegram({ type: form.type, title: form.title, body: form.body, zone: form.zone || undefined }),
    onSuccess: () => {
      setForm({ type: "oportunidades", title: "", body: "", zone: "" });
      setPreview(false);
      refetchLog();
    },
  });

  const weeklyMutation = useMutation({
    mutationFn: generateWeeklyReport,
    onSuccess: () => refetchLog(),
  });

  const previewText = `🏆 INFORME DE OPORTUNIDADES\n${"─".repeat(32)}\n${form.zone ? `🗺 Zona: ${form.zone}\n` : ""}<b>${form.title}</b>\n\n${form.body}`;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold text-gray-900">Comunicaciones</h1>

      {/* Auto-publicación */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col gap-3">
        <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
          Auto-publicación semanal
        </p>
        <p className="text-sm text-gray-500">
          Publica automáticamente los lunes y jueves a las 10:00h con los 5 mejores pisos
          no publicados en los últimos 14 días. Generado por Claude.
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={() => weeklyMutation.mutate()}
            disabled={weeklyMutation.isPending}
            className="text-sm bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {weeklyMutation.isPending ? "Generando..." : "▶ Ejecutar ahora"}
          </button>
          {weeklyMutation.isSuccess && (
            <span className="text-sm text-green-600">
              {weeklyMutation.data?.status === "sent"
                ? `✓ Publicado (${weeklyMutation.data.properties_featured} propiedades)`
                : (weeklyMutation.data as { reason?: string })?.reason ?? "Completado"}
            </span>
          )}
          {weeklyMutation.isError && (
            <span className="text-sm text-red-600">Error al generar</span>
          )}
        </div>
      </div>

      {/* Nueva publicación manual */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col gap-4">
        <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
          Nueva publicación manual
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700">Tipo</label>
            <select
              value={form.type}
              onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
              className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="oportunidades">Oportunidades</option>
              <option value="mercado">Mercado</option>
              <option value="zonas">Zonas</option>
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-gray-700">Zona (opcional)</label>
            <input
              value={form.zone}
              onChange={(e) => setForm((f) => ({ ...f, zone: e.target.value }))}
              placeholder="Ej: Eixample, Gràcia..."
              className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Título</label>
          <input
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="Resumen semanal · Mayo 2026"
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700">Cuerpo del mensaje</label>
          <textarea
            rows={6}
            value={form.body}
            onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
            placeholder="Contenido del informe..."
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {preview && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm font-mono whitespace-pre-wrap text-gray-700">
            {previewText}
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => setPreview((p) => !p)}
            className="text-sm border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {preview ? "Ocultar preview" : "Ver preview"}
          </button>
          <button
            onClick={() => publishMutation.mutate()}
            disabled={publishMutation.isPending || !form.title || !form.body}
            className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {publishMutation.isPending ? "Publicando..." : "Publicar en Telegram"}
          </button>
        </div>
        {publishMutation.isSuccess && (
          <p className="text-sm text-green-600">✓ Publicado en @inversorinformado</p>
        )}
      </div>

      {/* Historial */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <p className="font-semibold text-gray-800 text-sm uppercase tracking-wide">
            Historial de envíos
          </p>
        </div>
        {log.length === 0 ? (
          <p className="text-sm text-gray-400 px-5 py-6">Aún no hay mensajes enviados.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Fecha</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Tipo</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Mensaje</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {log.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-400 whitespace-nowrap">
                    {new Date(entry.sent_at).toLocaleString("es-ES")}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${TYPE_COLOR[entry.type] ?? "bg-gray-100 text-gray-600"}`}>
                      {TYPE_LABEL[entry.type] ?? entry.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-700 max-w-md truncate">
                    {entry.content}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${entry.status === "sent" ? "text-green-600" : "text-red-600"}`}>
                      {entry.status === "sent" ? "✓ Enviado" : "✗ Fallido"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
