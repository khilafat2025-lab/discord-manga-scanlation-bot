"use client";

import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { ArrowLeft, Download, Edit3, CheckCircle, XCircle, Zap, FileText } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

const STEP_ICONS: Record<string, string> = {
  extracting: "📄", ocr: "🔍", translating: "🌐",
  inpainting: "🎨", typesetting: "✍️", exporting: "📦",
  completed: "✅", failed: "❌", queue: "⏳",
};

export default function ProjectPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.id as string;
  const [project, setProject] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { router.push("/auth/login"); return; }
    fetchProject(token);
  }, [projectId]);

  useEffect(() => { logsEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  const fetchProject = async (token: string) => {
    try {
      const { data } = await axios.get(`${API_URL}/api/v1/projects/${projectId}`, { headers: { Authorization: `Bearer ${token}` } });
      setProject(data);
      if (data.job?.logs) setLogs(data.job.logs);
      if (data.status === "processing" || data.status === "pending") connectWebSocket(data.job?.id);
    } catch (err: any) {
      if (err.response?.status === 404) router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = (jobId: string) => {
    if (!jobId || wsRef.current) return;
    const ws = new WebSocket(`${WS_URL}/api/v1/projects/ws/${jobId}`);
    wsRef.current = ws;
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "log") setLogs(prev => [...prev, data.log]);
      else if (data.type === "progress") setProject((prev: any) => prev ? { ...prev, ...data.project } : prev);
      else if (data.type === "complete") { setProject((prev: any) => prev ? { ...prev, status: "completed" } : prev); ws.close(); }
    };
    ws.onclose = () => { wsRef.current = null; };
    const ping = setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send("ping"); else clearInterval(ping); }, 30000);
    return () => { ws.close(); clearInterval(ping); };
  };

  useEffect(() => { return () => { wsRef.current?.close(); }; }, []);

  if (loading) return <div className="min-h-screen manga-bg flex items-center justify-center"><div className="w-8 h-8 border-2 border-pink-500/30 border-t-pink-500 rounded-full animate-spin" /></div>;
  if (!project) return null;

  const progress = project.total_pages > 0 ? Math.round((project.processed_pages / project.total_pages) * 100) : 0;
  const isProcessing = ["pending", "processing"].includes(project.status);
  const isCompleted = project.status === "completed";
  const isFailed = project.status === "failed";

  return (
    <div className="min-h-screen manga-bg">
      <header className="glass border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="p-2 rounded-lg hover:bg-white/10"><ArrowLeft className="w-5 h-5 text-white/60" /></Link>
            <div>
              <h1 className="font-bold text-white text-sm">{project.title}</h1>
              <p className="text-xs text-white/40">{project.source_language} → {project.target_language}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isCompleted && (
              <>
                <a href={`${API_URL}/api/v1/projects/${projectId}/download`} className="btn-secondary text-sm py-2 px-3 flex items-center gap-1.5"><Download className="w-4 h-4" /> Download</a>
                <Link href={`/projects/${projectId}/editor`} className="btn-primary text-sm py-2 px-3 flex items-center gap-1.5"><Edit3 className="w-4 h-4" /> Edit</Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {isProcessing && <div className="w-3 h-3 rounded-full bg-blue-400 animate-pulse" />}
              {isCompleted && <CheckCircle className="w-5 h-5 text-green-400" />}
              {isFailed && <XCircle className="w-5 h-5 text-red-400" />}
              <span className="font-semibold text-white capitalize">{project.status}</span>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-white">{progress}%</div>
              <div className="text-xs text-white/40">{project.processed_pages}/{project.total_pages} pages</div>
            </div>
          </div>
          <div className="h-3 bg-white/10 rounded-full overflow-hidden mb-4">
            <motion.div
              className={`h-full rounded-full ${isCompleted ? "bg-green-500" : isFailed ? "bg-red-500" : "bg-gradient-to-r from-pink-500 to-purple-500"}`}
              initial={{ width: 0 }} animate={{ width: `${progress}%` }} transition={{ duration: 0.5 }}
            />
          </div>
          {project.job && (
            <div className="grid grid-cols-3 gap-4 text-center">
              <div><div className="text-lg font-bold text-white">{project.job.current_page || 0}</div><div className="text-xs text-white/40">Current Page</div></div>
              <div><div className="text-lg font-bold text-white">{project.job.pages_per_second?.toFixed(1) || "0.0"}</div><div className="text-xs text-white/40">Pages/sec</div></div>
              <div><div className="text-lg font-bold text-white">{project.job.estimated_seconds_remaining > 0 ? `${Math.ceil(project.job.estimated_seconds_remaining / 60)}m` : "—"}</div><div className="text-xs text-white/40">Remaining</div></div>
            </div>
          )}
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass rounded-2xl p-6">
          <h3 className="font-semibold text-white mb-4">Pipeline Steps</h3>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
            {["extracting", "ocr", "translating", "inpainting", "typesetting", "exporting"].map(step => {
              const stepOrder = ["extracting", "ocr", "translating", "inpainting", "typesetting", "exporting"];
              const currentIdx = stepOrder.indexOf(project.job?.current_step);
              const stepIdx = stepOrder.indexOf(step);
              const isDone = isCompleted || stepIdx < currentIdx;
              const isCurrent = step === project.job?.current_step;
              return (
                <div key={step} className={`text-center p-3 rounded-xl transition-all ${isDone ? "bg-green-500/20 border border-green-500/30" : isCurrent ? "bg-blue-500/20 border border-blue-500/30 animate-pulse" : "bg-white/5 border border-white/10"}`}>
                  <div className="text-xl mb-1">{STEP_ICONS[step]}</div>
                  <div className={`text-xs capitalize ${isDone ? "text-green-400" : isCurrent ? "text-blue-400" : "text-white/30"}`}>{step}</div>
                  {isDone && <div className="text-xs text-green-400">✓</div>}
                </div>
              );
            })}
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="glass rounded-2xl p-6">
          <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4 text-white/60" /> Live Logs
            {isProcessing && <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse ml-auto" />}
          </h3>
          <div className="log-terminal">
            {logs.length === 0 ? (
              <div className="text-white/30 text-center py-4">Waiting for logs...</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="text-white/30 flex-shrink-0 font-mono">{new Date(log.time).toLocaleTimeString()}</span>
                  <span className={`${log.message?.includes("✅") || log.message?.includes("🎉") ? "text-green-400" : log.message?.includes("❌") || log.message?.includes("⚠️") ? "text-red-400" : log.message?.includes("🌐") ? "text-blue-400" : "text-white/70"}`}>{log.message}</span>
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </motion.div>

        {isCompleted && (
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="glass rounded-2xl p-6 border border-green-500/30 bg-green-500/5">
            <div className="text-center">
              <div className="text-4xl mb-3">🎉</div>
              <h3 className="text-xl font-bold text-white mb-2">Translation Complete!</h3>
              <p className="text-white/50 mb-6">{project.total_pages} pages translated successfully</p>
              <div className="flex items-center justify-center gap-3">
                <a href={`${API_URL}/api/v1/projects/${projectId}/download`} className="btn-primary flex items-center gap-2"><Download className="w-4 h-4" /> Download</a>
                <Link href={`/projects/${projectId}/editor`} className="btn-secondary flex items-center gap-2"><Edit3 className="w-4 h-4" /> Edit Bubbles</Link>
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
