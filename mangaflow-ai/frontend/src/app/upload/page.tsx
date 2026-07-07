"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import axios from "axios";
import toast from "react-hot-toast";
import { Upload, FileText, X, Settings, Zap, ArrowLeft } from "lucide-react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const LANGUAGES = [
  { code: "ja", name: "Japanese" }, { code: "zh", name: "Chinese" },
  { code: "ko", name: "Korean" }, { code: "en", name: "English" },
  { code: "fr", name: "French" }, { code: "de", name: "German" },
  { code: "es", name: "Spanish" }, { code: "it", name: "Italian" },
  { code: "pt", name: "Portuguese" }, { code: "ru", name: "Russian" },
  { code: "ar", name: "Arabic" }, { code: "tr", name: "Turkish" },
  { code: "id", name: "Indonesian" }, { code: "hi", name: "Hindi" },
  { code: "ur", name: "Urdu" }, { code: "bn", name: "Bengali" },
  { code: "nl", name: "Dutch" }, { code: "th", name: "Thai" },
  { code: "vi", name: "Vietnamese" }, { code: "fa", name: "Persian" },
];

export default function UploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [sourceLang, setSourceLang] = useState("ja");
  const [targetLang, setTargetLang] = useState("en");
  const [exportFormat, setExportFormat] = useState("pdf");
  const [maintainHonorifics, setMaintainHonorifics] = useState(true);
  const [preserveSfx, setPreserveSfx] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback((accepted: File[]) => {
    const valid = accepted.filter(f => {
      const ext = f.name.split(".").pop()?.toLowerCase();
      if (!["pdf", "epub"].includes(ext || "")) { toast.error(`${f.name}: Only PDF/EPUB`); return false; }
      if (f.size > 2 * 1024 * 1024 * 1024) { toast.error(`${f.name}: Max 2GB`); return false; }
      return true;
    });
    setFiles(prev => [...prev, ...valid]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { "application/pdf": [".pdf"], "application/epub+zip": [".epub"] } });

  const handleUpload = async () => {
    if (files.length === 0) { toast.error("Select a file first"); return; }
    const token = localStorage.getItem("access_token");
    if (!token) { router.push("/auth/login"); return; }
    setUploading(true);
    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("source_language", sourceLang);
      formData.append("target_language", targetLang);
      formData.append("export_format", exportFormat);
      formData.append("maintain_honorifics", String(maintainHonorifics));
      formData.append("preserve_sfx", String(preserveSfx));
      try {
        const { data } = await axios.post(`${API_URL}/api/v1/projects/upload`, formData, {
          headers: { Authorization: `Bearer ${token}` },
          onUploadProgress: e => setUploadProgress(Math.round((e.loaded * 100) / (e.total || 1))),
        });
        toast.success(`${file.name} queued!`);
        router.push(`/projects/${data.project_id}`);
        return;
      } catch (err: any) {
        toast.error(err.response?.data?.detail || "Upload failed");
      }
    }
    setUploading(false);
  };

  return (
    <div className="min-h-screen manga-bg">
      <header className="glass border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center gap-4">
          <Link href="/dashboard" className="p-2 rounded-lg hover:bg-white/10"><ArrowLeft className="w-5 h-5 text-white/60" /></Link>
          <span className="font-bold text-white">New Translation</span>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3 space-y-4">
            <div {...getRootProps()} className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${isDragActive ? "drop-zone-active" : "border-white/20 hover:border-white/40 hover:bg-white/5"}`}>
              <input {...getInputProps()} />
              <Upload className="w-12 h-12 text-pink-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">{isDragActive ? "Drop here!" : "Upload Manga / Comic"}</h3>
              <p className="text-white/40 text-sm">PDF or EPUB · Max 2GB</p>
            </div>
            <AnimatePresence>
              {files.map((file, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="glass rounded-xl p-4 flex items-center gap-3">
                  <FileText className="w-8 h-8 text-pink-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{file.name}</p>
                    <p className="text-xs text-white/40">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                  </div>
                  <button onClick={() => setFiles(f => f.filter((_, j) => j !== i))} className="p-1.5 rounded-lg hover:bg-red-500/20 text-white/40 hover:text-red-400"><X className="w-4 h-4" /></button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          <div className="lg:col-span-2 space-y-4">
            <div className="glass rounded-2xl p-5 space-y-4">
              <h3 className="font-semibold text-white flex items-center gap-2"><Settings className="w-4 h-4 text-white/60" /> Settings</h3>
              <div>
                <label className="block text-xs text-white/50 mb-1.5">Source Language</label>
                <select value={sourceLang} onChange={e => setSourceLang(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-pink-500/50">
                  {LANGUAGES.map(l => <option key={l.code} value={l.code} className="bg-[#1a1a2e]">{l.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-white/50 mb-1.5">Target Language</label>
                <select value={targetLang} onChange={e => setTargetLang(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-white text-sm focus:outline-none focus:border-pink-500/50">
                  {LANGUAGES.map(l => <option key={l.code} value={l.code} className="bg-[#1a1a2e]">{l.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-white/50 mb-1.5">Export Format</label>
                <div className="grid grid-cols-3 gap-2">
                  {["pdf","epub","zip"].map(fmt => (
                    <button key={fmt} onClick={() => setExportFormat(fmt)} className={`py-2 rounded-xl text-sm font-medium transition-all ${exportFormat === fmt ? "bg-pink-500/30 text-pink-300 border border-pink-500/50" : "bg-white/5 text-white/50 border border-white/10 hover:bg-white/10"}`}>{fmt.toUpperCase()}</button>
                  ))}
                </div>
              </div>
              <div className="space-y-3 pt-2 border-t border-white/10">
                {[
                  { label: "Maintain Honorifics", value: maintainHonorifics, set: setMaintainHonorifics },
                  { label: "Preserve Sound Effects", value: preserveSfx, set: setPreserveSfx },
                ].map(t => (
                  <div key={t.label} className="flex items-center justify-between">
                    <span className="text-sm text-white">{t.label}</span>
                    <button onClick={() => t.set(!t.value)} className={`w-11 h-6 rounded-full transition-all relative ${t.value ? "bg-pink-500" : "bg-white/20"}`}>
                      <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${t.value ? "left-6" : "left-1"}`} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <button onClick={handleUpload} disabled={uploading || files.length === 0} className="btn-primary w-full flex items-center justify-center gap-2">
              {uploading ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> {uploadProgress}%</> : <><Zap className="w-4 h-4" /> Start Translation</>}
            </button>
            <p className="text-center text-xs text-white/30">Free: 20 pages/day · <Link href="/pricing" className="text-pink-400">Upgrade</Link></p>
          </div>
        </div>
      </main>
    </div>
  );
}
