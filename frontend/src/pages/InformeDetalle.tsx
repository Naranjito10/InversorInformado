import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  fetchReport, fetchReportHtmlBlob, downloadReportPdf, publishReportToTelegram
} from "../services/api";
import type { Report } from "../types";

export default function InformeDetalle() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [published, setPublished] = useState(false);
  const blobUrlRef = useRef<string | null>(null);

  const { data: report, isLoading } = useQuery<Report>({
    queryKey: ["report", id],
    queryFn: () => fetchReport(id!),
    enabled: !!id,
  });

  useEffect(() => {
    if (!id) return;
    fetchReportHtmlBlob(id)
      .then((url) => {
        setBlobUrl(url);
        blobUrlRef.current = url;
      })
      .catch((err) => {
        setPreviewError(err?.message ?? "Error al cargar el preview");
      });
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, [id]);

  const pdfMutation = useMutation({
    mutationFn: () => downloadReportPdf(id!, report?.title ?? "informe"),
  });

  const publishMutation = useMutation({
    mutationFn: () => publishReportToTelegram(id!),
    onSuccess: () => setPublished(true),
  });

  if (isLoading || !report) {
    return <p className="text-sm text-gray-400">Cargando informe...</p>;
  }

  const { property, market, scores } = report.data;

  return (
    <div className="flex flex-col gap-5">
      {/* Back nav */}
      <button
        onClick={() => navigate("/informes")}
        className="self-start flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors"
      >
        ← Volver a Informes
      </button>

      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center gap-4">
        <div className="flex-1">
          <h1 className="text-lg font-bold text-gray-900">{report.title}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {property.barrio}, {property.municipio} ·{" "}
            {property.precio?.toLocaleString("es-ES")} € ·{" "}
            {property.metros} m²
          </p>
          {market.ai_estimated && (
            <span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded mt-1 inline-block">
              Datos de mercado estimados por IA
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {scores?.global > 0 && (
            <span className={`text-sm font-bold px-3 py-1 rounded-full ${
              scores.global >= 80 ? "bg-green-100 text-green-700" :
              scores.global >= 60 ? "bg-yellow-100 text-yellow-700" :
              "bg-red-100 text-red-700"
            }`}>
              {scores.global}/100 · {scores.global_grade}
            </span>
          )}
          <button
            onClick={() => pdfMutation.mutate()}
            disabled={pdfMutation.isPending}
            className="text-sm border border-gray-300 text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            {pdfMutation.isPending ? "Generando..." : "↓ PDF"}
          </button>
          <button
            onClick={() => {
              if (window.confirm("¿Publicar este informe en el canal de Telegram?")) {
                publishMutation.mutate();
              }
            }}
            disabled={publishMutation.isPending || published}
            className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {published ? "✓ Publicado" : publishMutation.isPending ? "Publicando..." : "Publicar en Telegram"}
          </button>
        </div>
      </div>

      {publishMutation.isSuccess && (
        <p className="text-sm text-green-600 bg-green-50 px-4 py-2 rounded-lg">
          Publicado en @inversorinformado. Preview: {publishMutation.data?.preview}
        </p>
      )}

      {/* HTML Preview */}
      {blobUrl ? (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          <iframe
            src={blobUrl}
            title="Informe de análisis"
            className="w-full"
            style={{ height: "calc(297mm * 2 + 40px)", border: "none" }}
          />
        </div>
      ) : previewError ? (
        <div className="bg-red-50 border border-red-200 rounded-xl h-32 flex items-center justify-center">
          <p className="text-sm text-red-500">Error al cargar preview: {previewError}</p>
        </div>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-xl h-96 flex items-center justify-center">
          <p className="text-sm text-gray-400">Cargando preview...</p>
        </div>
      )}
    </div>
  );
}
