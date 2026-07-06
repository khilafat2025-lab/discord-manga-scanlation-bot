"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Zap, Mail, Lock, Github, Chrome, Eye, EyeOff, UserX } from "lucide-react";
import { authApi, setAuthTokens } from "@/lib/api";
import toast from "react-hot-toast";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const fn = mode === "login" ? authApi.login : authApi.register;
      const res = await fn({ email, password });
      setAuthTokens(res.data.access_token, res.data.refresh_token);
      toast.success(mode === "login" ? "Welcome back!" : "Account created!");
      router.push("/dashboard");
    } catch {
      // Error handled by interceptor
    } finally {
      setIsLoading(false);
    }
  };

  const handleGuest = async () => {
    setIsLoading(true);
    try {
      const res = await authApi.guest();
      setAuthTokens(res.data.access_token, res.data.refresh_token);
      toast.success("Continuing as guest (20 pages/day limit)");
      router.push("/dashboard");
    } catch {
      // handled
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen anime-bg flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center mx-auto mb-4 animate-pulse-glow">
            <Zap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">MangaFlow AI</h1>
          <p className="text-dark-400 mt-1">AI-powered manga translation</p>
        </div>

        <div className="glass-card p-8">
          <div className="flex bg-dark-800 rounded-xl p-1 mb-6">
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all capitalize ${
                  mode === m ? "bg-brand-500 text-white" : "text-dark-400 hover:text-white"
                }`}
              >
                {m === "login" ? "Sign In" : "Sign Up"}
              </button>
            ))}
          </div>

          <div className="space-y-3 mb-6">
            <a
              href="/api/v1/auth/google"
              className="flex items-center justify-center gap-3 w-full py-3 bg-dark-800 hover:bg-dark-700 border border-dark-600 rounded-xl text-white font-medium transition-all"
            >
              <Chrome className="w-5 h-5 text-red-400" />
              Continue with Google
            </a>
            <a
              href="/api/v1/auth/github"
              className="flex items-center justify-center gap-3 w-full py-3 bg-dark-800 hover:bg-dark-700 border border-dark-600 rounded-xl text-white font-medium transition-all"
            >
              <Github className="w-5 h-5" />
              Continue with GitHub
            </a>
          </div>

          <div className="flex items-center gap-3 mb-6">
            <div className="flex-1 h-px bg-dark-700" />
            <span className="text-dark-500 text-sm">or</span>
            <div className="flex-1 h-px bg-dark-700" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-dark-300 text-sm mb-1.5 block">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full bg-dark-800 border border-dark-600 text-white rounded-xl pl-10 pr-4 py-3 focus:border-brand-500 focus:outline-none placeholder:text-dark-500"
                />
              </div>
            </div>
            <div>
              <label className="text-dark-300 text-sm mb-1.5 block">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={8}
                  className="w-full bg-dark-800 border border-dark-600 text-white rounded-xl pl-10 pr-12 py-3 focus:border-brand-500 focus:outline-none placeholder:text-dark-500"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-white"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-gradient-to-r from-brand-500 to-accent-cyan text-white font-bold rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                mode === "login" ? "Sign In" : "Create Account"
              )}
            </button>
          </form>

          <button
            onClick={handleGuest}
            disabled={isLoading}
            className="w-full mt-3 py-3 bg-dark-800 hover:bg-dark-700 border border-dark-600 text-dark-300 hover:text-white font-medium rounded-xl transition-all flex items-center justify-center gap-2"
          >
            <UserX className="w-4 h-4" />
            Continue as Guest (20 pages/day)
          </button>
        </div>

        <p className="text-center text-dark-400 text-sm mt-6">
          Need unlimited pages?{" "}
          <Link href="/pricing" className="text-brand-400 hover:text-brand-300">
            View pricing →
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
