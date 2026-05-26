import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  testPortal, fetchLogs, fetchFuentes, createFuente, toggleFuente, deleteFuente, updateFuente,
} from "../services/api";
import type { PortalTestResult, LogEntry, Fuente } from "../services/api";

const IconEdit = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
);

const IconTrash = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
    <path d="M10 11v6M14 11v6"/>
    <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
  </svg>
);
import Modal from "../components/Modal";
import ConfirmDialog from "../components/ConfirmDialog";

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

// ---------------------------------------------------------------------------
// Monitor tab
// ---------------------------------------------------------------------------

function PortalCard({ portal, nombre }: { portal: string; nombre: string }) {
  const [result, setResult] = useState<PortalTestResult | null>(null);

  const mutation = useMutation({
    mutationFn: () => testPortal(portal),
    onSuccess: (data) => setResult(data),
  });

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-gray-800">{nombre}</span>
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

  const extras = Object.entries(entry).filter(
    ([k]) => !["ts", "level", "logger", "msg", "raw"].includes(k)
  );

  return (
    <div className="flex gap-3 py-2 border-b border-gray-50 text-xs font-mono">
      <span className="text-gray-300 shrink-0 w-20">{formatTs(entry.ts as string)}</span>
      <span className={`shrink-0 w-16 ${LEVEL_STYLE[level] ?? LEVEL_STYLE.INFO}`}>{level}</span>
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

function MonitorTab() {
  const [logLines, setLogLines] = useState(50);

  const fuentesQuery = useQuery({
    queryKey: ["fuentes"],
    queryFn: () => fetchFuentes(),
  });

  const logsQuery = useQuery({
    queryKey: ["logs", logLines],
    queryFn: () => fetchLogs(logLines),
    refetchInterval: 30_000,
  });

  const portales = (fuentesQuery.data ?? []).filter(
    (f) => f.activo && f.id !== "manual"
  );

  return (
    <div className="flex flex-col gap-8">
      {/* Portales */}
      <section className="flex flex-col gap-3">
        <h2 className="text-base font-semibold text-gray-700">Estado de portales</h2>
        {fuentesQuery.isLoading ? (
          <p className="text-sm text-gray-400">Cargando portales…</p>
        ) : portales.length === 0 ? (
          <p className="text-sm text-gray-400">No hay portales activos configurados.</p>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {portales.map((f) => (
              <PortalCard key={f.id} portal={f.id} nombre={f.nombre} />
            ))}
          </div>
        )}
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
              className="capitalize text-xs border border-gray-300 rounded-lg px-2 py-1.5 text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
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

// ---------------------------------------------------------------------------
// Portales tab
// ---------------------------------------------------------------------------

function slugify(nombre: string): string {
  return nombre
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function PortalesTab() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [nombre, setNombre] = useState("");
  const [testUrl, setTestUrl] = useState("");

  const fuentesQuery = useQuery({
    queryKey: ["fuentes"],
    queryFn: () => fetchFuentes(),
  });

  const closeModal = () => {
    setModalOpen(false);
    setNombre(""); setTestUrl("");
  };

  const createMut = useMutation({
    mutationFn: () => createFuente(slugify(nombre.trim()), nombre.trim(), testUrl.trim() || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fuentes"] });
      closeModal();
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({ fid, activo }: { fid: string; activo: boolean }) =>
      toggleFuente(fid, activo),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["fuentes"] }),
  });

  const [deleteTarget, setDeleteTarget] = useState<Fuente | null>(null);

  const deleteMut = useMutation({
    mutationFn: (fid: string) => deleteFuente(fid),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fuentes"] });
      setDeleteTarget(null);
    },
  });

  const [editFuente, setEditFuente] = useState<Fuente | null>(null);
  const [editNombre, setEditNombre] = useState("");
  const [editTestUrl, setEditTestUrl] = useState("");

  const openEdit = (f: Fuente) => {
    setEditFuente(f);
    setEditNombre(f.nombre);
    setEditTestUrl(f.test_url ?? "");
  };
  const closeEdit = () => setEditFuente(null);

  const updateMut = useMutation({
    mutationFn: () => updateFuente(editFuente!.id, editNombre.trim(), editTestUrl.trim() || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fuentes"] });
      closeEdit();
    },
  });

  const fuentes: Fuente[] = fuentesQuery.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-end">
        <button
          onClick={() => setModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Añadir portal
        </button>
      </div>

      {/* Lista */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        {fuentesQuery.isLoading ? (
          <p className="text-sm text-gray-400 text-center py-10">Cargando…</p>
        ) : fuentes.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-10">Sin portales configurados.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Nombre</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">URL de test</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500">Activo</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {fuentes.map((f) => (
                <tr key={f.id} className="border-b border-gray-100 last:border-0">
                  <td className="px-4 py-3 font-medium text-gray-800">{f.nombre}</td>
                  <td className="px-4 py-3 max-w-xs">
                    {f.test_url ? (
                      <a
                        href={f.test_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-blue-500 hover:underline truncate block"
                      >
                        {f.test_url}
                      </a>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => toggleMut.mutate({ fid: f.id, activo: !f.activo })}
                      disabled={toggleMut.isPending}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                        f.activo ? "bg-blue-500" : "bg-gray-300"
                      }`}
                    >
                      <span
                        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                          f.activo ? "translate-x-4" : "translate-x-1"
                        }`}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-3">
                      <button
                        onClick={() => openEdit(f)}
                        className="text-gray-400 hover:text-blue-600 transition-colors"
                        title="Editar"
                      >
                        <IconEdit />
                      </button>
                      <button
                        onClick={() => setDeleteTarget(f)}
                        className="text-gray-400 hover:text-red-600 transition-colors"
                        title="Eliminar"
                      >
                        <IconTrash />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal isOpen={!!editFuente} onClose={closeEdit} title="Editar portal">
        <form
          onSubmit={(e) => { e.preventDefault(); updateMut.mutate(); }}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-gray-500">Nombre</label>
            <input
              required
              autoFocus
              value={editNombre}
              onChange={(e) => setEditNombre(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-gray-500">URL de test</label>
            <input
              type="url"
              placeholder="https://..."
              value={editTestUrl}
              onChange={(e) => setEditTestUrl(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {updateMut.isError && (
            <p className="text-xs text-red-500">Error al guardar los cambios.</p>
          )}
          <div className="flex gap-2 justify-end pt-1">
            <button
              type="button"
              onClick={closeEdit}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={updateMut.isPending || !editNombre.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {updateMut.isPending ? "Guardando…" : "Guardar"}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteMut.mutate(deleteTarget!.id)}
        loading={deleteMut.isPending}
        title="Eliminar portal"
        message={`¿Seguro que quieres eliminar "${deleteTarget?.nombre}"? Esta acción no se puede deshacer.`}
      />

      <Modal isOpen={modalOpen} onClose={closeModal} title="Añadir portal">
        <form
          onSubmit={(e) => { e.preventDefault(); createMut.mutate(); }}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-gray-500">Nombre</label>
            <input
              required
              autoFocus
              placeholder="Mi Portal"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-gray-500">URL de test</label>
            <input
              type="url"
              placeholder="https://www.mi-portal.com/venta/pisos-barcelona/"
              value={testUrl}
              onChange={(e) => setTestUrl(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-400">URL que se usa en Monitor para probar la conexión con el portal.</p>
          </div>
          {createMut.isError && (
            <p className="text-xs text-red-500">Error al añadir el portal.</p>
          )}
          <div className="flex gap-2 justify-end pt-1">
            <button
              type="button"
              onClick={closeModal}
              className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createMut.isPending || !nombre.trim()}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {createMut.isPending ? "Añadiendo…" : "Añadir"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type Tab = "monitor" | "portales";

export default function Monitor() {
  const [tab, setTab] = useState<Tab>("monitor");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Monitor</h1>
        <p className="text-sm text-gray-400 mt-1">Estado de portales y logs del sistema</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {(["monitor", "portales"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t
                ? "bg-white text-gray-800 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "monitor" ? "Monitor" : "Portales"}
          </button>
        ))}
      </div>

      {tab === "monitor" ? <MonitorTab /> : <PortalesTab />}
    </div>
  );
}
