"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { Check, Zap, Crown, ArrowLeft } from "lucide-react";

const FREE_FEATURES = ["20 pages per day","PDF & EPUB support","10+ languages","Basic OCR","Standard translation","ZIP export"];
const PREMIUM_FEATURES = ["Unlimited pages","PDF, EPUB & ZIP export","100+ languages","MangaOCR + PaddleOCR","GPT-4o / Gemini AI","Context-aware translation","Honorifics & glossary","Bubble editor","Priority queue","API access","Resume interrupted jobs","30-day file retention"];

export default function PricingPage() {
  return (
    <div className="min-h-screen manga-bg">
      <header className="glass border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 h-16 flex items-center gap-4">
          <Link href="/dashboard" className="p-2 rounded-lg hover:bg-white/10"><ArrowLeft className="w-5 h-5 text-white/60" /></Link>
          <div className="flex items-center gap-2"><Zap className="w-5 h-5 text-pink-400" /><span className="font-bold text-white">Pricing</span></div>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">Simple, Transparent Pricing</h1>
          <p className="text-white/50 text-lg">Start free, upgrade when you need more</p>
        </motion.div>
        <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="glass rounded-2xl p-8">
            <h2 className="text-xl font-bold text-white mb-1">Free</h2>
            <div className="text-4xl font-bold text-white mb-4">$0<span className="text-lg text-white/40 font-normal">/mo</span></div>
            <ul className="space-y-3 mb-8">{FREE_FEATURES.map(f => <li key={f} className="flex items-center gap-2 text-sm text-white/70"><Check className="w-4 h-4 text-green-400 flex-shrink-0" />{f}</li>)}</ul>
            <Link href="/auth/register" className="btn-secondary w-full text-center block py-3 rounded-xl">Get Started Free</Link>
          </motion.div>
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="relative rounded-2xl p-8 bg-gradient-to-br from-pink-500/20 to-purple-500/20 border border-pink-500/30">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2"><span className="bg-gradient-to-r from-pink-500 to-purple-600 text-white text-xs font-bold px-4 py-1 rounded-full">MOST POPULAR</span></div>
            <div className="flex items-center gap-2 mb-1"><Crown className="w-5 h-5 text-yellow-400" /><h2 className="text-xl font-bold text-white">Premium</h2></div>
            <div className="text-4xl font-bold text-white mb-4">$12<span className="text-lg text-white/40 font-normal">/mo</span></div>
            <ul className="space-y-3 mb-8">{PREMIUM_FEATURES.map(f => <li key={f} className="flex items-center gap-2 text-sm text-white/80"><Check className="w-4 h-4 text-pink-400 flex-shrink-0" />{f}</li>)}</ul>
            <button className="btn-primary w-full">Upgrade to Premium</button>
          </motion.div>
        </div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="text-center text-white/30 text-sm mt-8">
          Cancel anytime · Secure payment via Stripe · 7-day money-back guarantee
        </motion.p>
      </main>
    </div>
  );
}
