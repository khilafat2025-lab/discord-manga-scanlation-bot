"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import toast from "react-hot-toast";
import { Upload, BookOpen, CheckCircle, XCircle, Trash2, Download, Eye, Plus, Zap } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  pending:    { label: "Pending",    color: "badge-queued" },
  processing: { label: "Processing", color: "badge-processing" },
  completed:  { label: "Done",       color: "badge-completed" },
  failed:     { label: "Failed",     color: "badge-failed" },
  cancelled:  { label: "Cancelled",  color: "badge-failed" },
};

export default function DashboardPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const userData = localStorage.getItem("user");
    if (!token) { router.push("/auth/login"); return; }
    if (userData) setUser(JSON.parse(userData));
    fetchProjects(token);
  }, []);

  const fetchProjects = async (token: string) => {
    try {
      const { data } = await axios.get(`${API_URL}/api/v1/projects/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setProjects(data.projects || []);
    } catch (err: any) {
      if (err.response?.status === 401) router.push("/auth/login");
      else toast.error("Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  const deleteProject = async (id: string) => {
    const token = localStorage.getItem("access_token");
    try {
      await axios.delete(`${API_URL}/api/v1/projects/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      setProjects(prev => prev.filter(p => p.id !== id));
      toast.success("Project deleted");
    } catch { toast.error("Delete failed"); }
  };

  const stats = {
    total: projects.length,
    completed: projects.filter(p => p.status === "completed").length,
    processing: projects.filter(p => p.status === "processing").length,
    failed: projects.filter(p => p.status === "failed").length,
  };

  return (
    <div className="min-h-screen manga-bg">
      <header className="glass border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-lg bg-gradient-to-r from-pink-400 to-purple-400 bg-clip-text text-transparent">MangaFlow AI</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-white/50 hidden sm:block">{user?.email || "Guest"}</span>
            <Link href="/upload" className="btn-primary text-sm py-2 px-4 flex items-center gap-2">
              <Plus className="w-4 h-4" /> New Translation
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total", value: stats.total, color: "text-blue-400" },
            { label: "Completed", value: stats.completed, color: "text-green-400" },
            { label: "Processing", value: stats.processing, color: "text-yellow-400" },
            { label: "Failed", value: stats.failed, color: "text-red-400" },
          ].map((s, i) => (
            <motion.div key={s.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }} className="manga-card">
              <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-sm text-white/50">{s.label}</div>
            </motion.div>
          ))}
        </motion.div>

        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">Recent Projects</h2>
          <Link href="/upload" className="text-sm text-pink-400 hover:text-pink-300 flex items-center gap-1">
            <Upload className="w-4 h-4" /> Upload New
          </Link>
        </div>

        {loading ? (
          <div className="space-y-4">{[1,2,3].map(i => <div key={i} className="glass rounded-2xl p-6 shimmer h-24" />)}</div>
        ) : projects.length === 0 ? (
          <div className="text-center py-20">
            <BookOpen className="w-16 h-16 text-white/10 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white/40 mb-4">No projects yet</h3>
            <Link href="/upload" className="btn-primary inline-flex items-center gap-2"><Upload className="w-4 h-4" /> Upload Manga</Link>
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map((project, i) => {
              const status = STATUS_CONFIG[project.status] || STATUS_CONFIG.pending;
              const progress = project.total_pages > 0 ? Math.round((project.processed_pages / project.total_pages) * 100) : 0;
              return (
                <motion.div key={project.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} className="glass rounded-2xl p-5 hover:bg-white/8 transition-all group">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-pink-500/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                      <BookOpen className="w-6 h-6 text-pink-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-white truncate">{project.title}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${status.color}`}>{status.label}</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-white/40">
                        <span>{project.file_type.toUpperCase()}</span>
                        <span>•</span>
                        <span>{project.source_language} → {project.target_language}</span>
                        <span>•</span>
                        <span>{project.total_pages} pages</span>
                        <span>•</span>
                        <span>{formatDistanceToNow(new Date(project.created_at), { addSuffix: true })}</span>
                      </div>
                      {project.status === "processing" && (
                        <div className="mt-2">
                          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-pink-500 to-purple-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      {project.status === "processing" && (
                        <Link href={`/projects/${project.id}`} className="p-2 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors"><Eye className="w-4 h-4" /></Link>
                      )}
                      {project.status === "completed" && (
                        <a href={`${API_URL}/api/v1/projects/${project.id}/download`} className="p-2 rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors"><Download className="w-4 h-4" /></a>
                      )}
                      <button onClick={() => deleteProject(project.id)} className="p-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
