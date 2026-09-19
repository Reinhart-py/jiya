import json
import os
import threading
import time
import webbrowser
from typing import Any, Dict, List
import webview

from gmaps.runner import GMapsRunner
from runner.runner import Runner as TwoGISRunner
from utils.paths import get_app_dir, get_export_dir
from utils.security import get_saved_key, revoke_saved_key, save_key, verify_key_payload
from utils.state_manager import (
    clear_active_checkpoint,
    get_active_checkpoint,
    load_all_history,
)

HTML_UI = """<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Kiri Enterprise</title>
<script src="https://cdn.tailwindcss.com?plugins=forms"></script>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
<script>
tailwind.config = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        forest: {
          sidebar: '#111714',
          sidebarCard: '#17221C',
          activeNav: '#1C2821',
          border: '#1E2B23',
          emerald: '#20C063',
          emeraldDark: '#147A40',
          bg: '#F5F8F6',
          card: '#FFFFFF',
          cardBorder: '#E3ECE6',
          cardMuted: '#DCEEE3',
        }
      }
    }
  }
}
</script>
<style>
body { font-family: 'Plus Jakarta Sans', sans-serif; -webkit-font-smoothing: antialiased; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(100, 116, 139, 0.25); border-radius: 9999px; }
.viewport-radial-bg {
  background-color: #0B2416;
  background-image: radial-gradient(circle at 50% 50%, #135A33 0%, #0A2E1A 45%, #05160C 100%);
}
</style>
</head>
<body class="viewport-radial-bg h-full flex items-center justify-center p-2 sm:p-4 selection:bg-emerald-500 selection:text-white select-none">

<div id="view-auth" class="w-full max-w-[460px] bg-white rounded-[32px] p-8 sm:p-10 shadow-2xl text-center flex flex-col items-center border border-neutral-100 transition-all duration-300">
  <div class="mb-6 flex items-center justify-center">
    <div class="w-10 h-10 rounded-2xl bg-neutral-900 flex items-center justify-center shadow-sm">
      <div class="flex items-center space-x-1">
        <span class="w-1 h-4 bg-white rounded-full"></span>
        <span class="w-1 h-3 bg-white/70 rounded-full"></span>
        <span class="w-1 h-2 bg-white/40 rounded-full"></span>
      </div>
    </div>
    <span class="ml-2.5 text-xl font-bold tracking-tight text-neutral-900">Kiri</span>
  </div>

  <h1 class="text-2xl font-bold tracking-tight text-neutral-900">Enter License Key</h1>
  <p class="text-sm text-neutral-500 mt-2 leading-relaxed max-w-xs">
    Please enter your license key below to activate and continue using Kiri.
  </p>

  <form class="w-full mt-7 space-y-3" onsubmit="event.preventDefault(); window.submitAuth();">
    <div>
      <input id="auth-key-input" autocomplete="off" spellcheck="false" placeholder="XXXX-XXXX-XXXX-XXXX" class="w-full text-center tracking-widest font-mono text-sm px-4 py-3.5 bg-neutral-50 border border-neutral-200 rounded-xl text-neutral-900 placeholder-neutral-400 focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900 transition-all" type="text"/>
    </div>
    <div id="auth-error" class="text-xs text-rose-500 font-medium min-h-[18px]"></div>
    <button id="auth-submit-btn" type="submit" class="w-full py-3.5 px-4 bg-neutral-900 hover:bg-neutral-800 active:bg-black text-white text-sm font-semibold rounded-xl transition-all shadow-sm">
      Activate
    </button>
  </form>

  <div class="w-full mt-8 pt-6 border-t border-neutral-100">
    <p class="text-xs text-neutral-400 mb-3">Don't have a key or need a renewal?</p>
    <div class="grid grid-cols-2 gap-3">
      <button onclick="window.pywebview.api.open_link('https://wa.me/13153701897')" class="flex items-center justify-center space-x-2 py-2.5 px-3 rounded-xl border border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50 text-neutral-700 transition-all text-xs font-medium">
        <svg class="w-4 h-4 text-emerald-600 fill-current shrink-0" viewBox="0 0 24 24"><path d="M12.031 6.172c-3.181 0-5.767 2.586-5.768 5.766-.001 1.298.38 2.27 1.019 3.287l-.711 2.599 2.679-.702c.972.575 1.761.882 2.781.882h.001c3.182 0 5.767-2.587 5.768-5.766 0-3.182-2.586-5.766-5.769-5.766zm3.374 8.167c-.145.407-.84.773-1.157.822-.317.049-.731.074-2.146-.511-1.705-.705-2.793-2.457-2.879-2.571-.086-.114-.689-.916-.689-1.747 0-.831.436-1.24.592-1.409.155-.169.34-.212.453-.212.113 0 .227 0 .327.006.105.005.244-.04.382.291.144.346.491 1.196.534 1.282.043.086.072.188.014.303-.058.115-.087.188-.173.288-.087.1-.182.224-.26.3-.087.086-.178.18-.077.353.101.173.449.741.964 1.2.663.591 1.222.774 1.395.86.173.086.275.072.376-.044.101-.115.433-.504.549-.677.116-.173.231-.144.39-.086.159.058 1.01.476 1.184.563.173.087.289.13.332.202.044.072.044.419-.101.826z"></path><path d="M12 2C6.477 2 2 6.477 2 12c0 1.891.528 3.662 1.448 5.176L2 22l4.981-1.306A9.957 9.957 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18.067c-1.637 0-3.15-.497-4.409-1.353l-.316-.217-2.957.773.789-2.885-.236-.376A8.026 8.026 0 014 12c0-4.411 3.589-8.067 8-8.067s8 3.656 8 8.067-3.589 8.067-8 8.067z"></path></svg>
        <span>WhatsApp</span>
      </button>
      <button onclick="window.pywebview.api.open_link('https://t.me/kiri0507')" class="flex items-center justify-center space-x-2 py-2.5 px-3 rounded-xl border border-neutral-200 hover:border-neutral-300 hover:bg-neutral-50 text-neutral-700 transition-all text-xs font-medium">
        <svg class="w-4 h-4 text-sky-500 fill-current shrink-0" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"></path></svg>
        <span>Telegram</span>
      </button>
    </div>
  </div>
</div>

<main id="view-app" class="hidden w-full max-w-[1440px] h-[94vh] rounded-[32px] bg-forest-sidebar shadow-2xl border border-[#1B2821] flex overflow-hidden text-neutral-900">

  <aside class="w-[260px] bg-forest-sidebar flex-shrink-0 flex flex-col justify-between p-5 border-r border-[#1B2821] text-slate-300">
    <div class="space-y-5">
      <div class="flex items-center gap-2.5 px-1">
        <div class="flex items-end gap-[3px] h-5">
          <span class="w-[3.5px] h-3 bg-forest-emerald rounded-full"></span>
          <span class="w-[3.5px] h-5 bg-forest-emerald rounded-full"></span>
          <span class="w-[3.5px] h-4 bg-forest-emerald rounded-full"></span>
        </div>
        <span class="text-white text-lg font-bold tracking-tight">Kiri</span>
        <span id="ui-license-pill" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-forest-sidebarCard border border-[#23332A] text-forest-emerald">PRO</span>
      </div>

      <div class="bg-forest-sidebarCard rounded-2xl p-2.5 flex items-center justify-between border border-[#23332A]">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-[#1ea857] to-[#146b38] flex items-center justify-center text-white font-bold text-xs shadow-inner">
            K
          </div>
          <div>
            <div class="text-[10px] text-gray-400 font-medium leading-none">License Node</div>
            <div id="sidebar-owner-name" class="text-xs text-white font-semibold tracking-wide mt-1 truncate max-w-[120px]">Active Node</div>
          </div>
        </div>
      </div>

      <nav class="space-y-1 text-[13px] font-medium" id="nav-container">
        <button onclick="switchTab('dashboard')" id="nav-dashboard" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl bg-forest-activeNav text-white border border-[#26372D] shadow-sm transition-all">
          <svg class="w-4 h-4 text-forest-emerald" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
          <span>Dashboard</span>
        </button>
        <button onclick="switchTab('gmaps')" id="nav-gmaps" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-[#16221B] transition-all">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path><path d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
          <span>Google Maps</span>
        </button>
        <button onclick="switchTab('twogis')" id="nav-twogis" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-[#16221B] transition-all">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
          <span>2GIS Global</span>
        </button>
        <button onclick="switchTab('history')" id="nav-history" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-[#16221B] transition-all">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
          <span>Checkpoints</span>
        </button>
        <button onclick="switchTab('developer')" id="nav-developer" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-[#16221B] transition-all">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
          <span>Developer Dossier</span>
        </button>
      </nav>
    </div>

    <div class="pt-4 border-t border-[#19241E] space-y-3">
      <div class="flex items-center justify-between px-2 py-1.5 rounded-xl hover:bg-[#16211A] transition-colors">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-full overflow-hidden border border-forest-border flex-shrink-0">
            <img src="https://ik.imagekit.io/Reinhart/reinhart.png?updatedAt=1747593545727" class="w-full h-full object-cover"/>
          </div>
          <div class="leading-tight">
            <h4 class="text-xs font-semibold text-white">Reinhart</h4>
            <p id="sidebar-expiry-text" class="text-[10px] text-gray-400 truncate max-w-[110px]">Verified Key</p>
          </div>
        </div>
        <button onclick="window.logoutLicense()" title="Purge Key" class="text-gray-500 hover:text-rose-400 transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg>
        </button>
      </div>
    </div>
  </aside>

  <div class="flex-1 bg-forest-bg p-5 sm:p-7 flex flex-col gap-5 overflow-y-auto max-h-[94vh]">

    <div id="tab-dashboard" class="space-y-5">
      <header class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight text-neutral-900">Dashboard</h1>
          <p class="text-xs text-neutral-500 mt-0.5">High-velocity directory mining and intelligence stream</p>
        </div>
        <div class="flex items-center gap-2">
          <span id="system-status-indicator" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Engine Ready
          </span>
        </div>
      </header>

      <div id="recovery-banner" class="hidden bg-neutral-900 text-white rounded-2xl p-4 flex items-center justify-between shadow-lg border border-neutral-800">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-xl bg-forest-emerald flex items-center justify-center text-black font-bold">
            !
          </div>
          <div>
            <h4 class="text-xs font-bold uppercase tracking-wider text-forest-emerald">Checkpoint Recovery Available</h4>
            <p id="recovery-banner-text" class="text-xs text-neutral-300 mt-0.5">Session halted unexpectedly.</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button onclick="window.resumeActiveCheckpoint()" class="px-4 py-2 rounded-xl bg-forest-emerald hover:bg-emerald-400 text-neutral-900 font-bold text-xs transition-all">
            Resume Immediately
          </button>
          <button onclick="window.dismissActiveCheckpoint()" class="px-3 py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-medium transition-all">
            Dismiss
          </button>
        </div>
      </div>

      <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-forest-sidebar text-white rounded-[24px] p-5 flex justify-between items-stretch shadow-sm border border-[#1b2b22] relative overflow-hidden">
          <div class="flex flex-col justify-between z-10">
            <span class="text-xs font-medium text-gray-400">Total Harvested</span>
            <div>
              <div id="stat-total-leads" class="text-3xl font-bold tracking-tight text-white mt-1">0</div>
              <div class="flex items-center gap-1 text-[11px] font-medium text-forest-emerald mt-1.5">
                <span>Direct B2B verified numbers</span>
              </div>
            </div>
          </div>
          <div class="flex items-end gap-1.5 pl-2 z-10 self-end mb-1">
            <div class="w-2.5 h-10 bg-forest-emerald rounded-full"></div>
            <div class="w-2.5 h-6 bg-forest-emerald rounded-full"></div>
            <div class="w-2.5 h-8 bg-forest-emerald rounded-full"></div>
          </div>
        </div>

        <div class="bg-white rounded-[24px] p-5 flex justify-between items-stretch border border-forest-cardBorder shadow-sm">
          <div class="flex flex-col justify-between">
            <span class="text-xs font-medium text-gray-500">Completed Sessions</span>
            <div>
              <div id="stat-total-sessions" class="text-3xl font-bold tracking-tight text-gray-900 mt-1">0</div>
              <div class="flex items-center gap-1 text-[11px] font-medium text-emerald-600 mt-1.5">
                <span>Checkpoints stored</span>
              </div>
            </div>
          </div>
          <div class="flex items-end gap-1.5 pl-2 self-end mb-1">
            <div class="w-2.5 h-5 bg-emerald-200 rounded-full"></div>
            <div class="w-2.5 h-8 bg-emerald-400 rounded-full"></div>
            <div class="w-2.5 h-6 bg-forest-emerald rounded-full"></div>
          </div>
        </div>

        <div class="bg-white rounded-[24px] p-5 flex justify-between items-stretch border border-forest-cardBorder shadow-sm">
          <div class="flex flex-col justify-between">
            <span class="text-xs font-medium text-gray-500">License Expiration</span>
            <div>
              <div id="stat-expiry-text" class="text-sm font-bold tracking-tight text-gray-900 mt-1.5 truncate max-w-[200px]">Validating...</div>
              <div id="stat-owner-text" class="text-[11px] font-medium text-gray-400 mt-1.5 truncate max-w-[200px]">Registered Node</div>
            </div>
          </div>
          <div class="w-9 h-9 rounded-full bg-forest-cardMuted flex items-center justify-center text-forest-emeraldDark font-bold self-center">
            ✓
          </div>
        </div>
      </section>

      <section class="bg-white rounded-[28px] p-5 border border-forest-cardBorder shadow-sm flex flex-col justify-between space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-forest-emerald"></span>
            <h3 class="text-sm font-bold text-gray-900">Realtime Execution Stream</h3>
          </div>
          <span class="text-[11px] text-gray-400 font-mono" id="stream-clock">Ready</span>
        </div>
        <div id="console-stream" class="w-full h-72 bg-[#0C120E] text-emerald-400 font-mono text-xs rounded-2xl p-4 overflow-y-auto leading-relaxed border border-[#17251C] shadow-inner space-y-1">
          <div class="text-gray-500">System standby. Initiate a module run or resume from checkpoint.</div>
        </div>
      </section>
    </div>

    <div id="tab-gmaps" class="hidden space-y-5">
      <header>
        <h1 class="text-2xl font-bold tracking-tight text-neutral-900">Google Maps Lead Miner</h1>
        <p class="text-xs text-neutral-500 mt-0.5">Automated map card parser with rate-limit evasion and single-match recovery</p>
      </header>

      <div class="bg-white rounded-[28px] p-6 border border-forest-cardBorder shadow-sm space-y-5">
        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">Target Query, Maps URL, or Batch File</label>
          <div class="flex gap-2">
            <input id="gmaps-input" type="text" class="flex-1 bg-neutral-50 border border-neutral-200 rounded-xl px-4 py-3 text-sm text-neutral-900 focus:outline-none focus:ring-1 focus:ring-forest-emerald" value="Software in Business Bay"/>
            <button onclick="window.selectBatchFile()" class="px-5 py-3 rounded-xl bg-forest-sidebar text-white font-semibold text-xs hover:bg-[#1A2620] transition-colors border border-forest-border">
              Browse
            </button>
          </div>
        </div>

        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">Extraction Limit (0 for continuous / unlimited)</label>
          <input id="gmaps-cap" type="number" class="w-48 bg-neutral-50 border border-neutral-200 rounded-xl px-4 py-3 text-sm text-neutral-900 focus:outline-none focus:ring-1 focus:ring-forest-emerald" value="1000"/>
        </div>

        <button onclick="window.runGmaps()" id="gmaps-submit-btn" class="px-6 py-3.5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-bold text-xs tracking-wide transition-all shadow-sm">
          Start Google Maps Scraper
        </button>
      </div>
    </div>

    <div id="tab-twogis" class="hidden space-y-5">
      <header>
        <h1 class="text-2xl font-bold tracking-tight text-neutral-900">2GIS Regional Extractor</h1>
        <p class="text-xs text-neutral-500 mt-0.5">Directory mining across UAE, Russia, Kazakhstan with viewport locking</p>
      </header>

      <div class="bg-white rounded-[28px] p-6 border border-forest-cardBorder shadow-sm space-y-5">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">Emirate / City Name</label>
            <input id="twogis-city" type="text" class="w-full bg-neutral-50 border border-neutral-200 rounded-xl px-4 py-3 text-sm text-neutral-900 focus:outline-none focus:ring-1 focus:ring-forest-emerald" value="Dubai"/>
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">Query Taxonomy</label>
            <input id="twogis-query" type="text" class="w-full bg-neutral-50 border border-neutral-200 rounded-xl px-4 py-3 text-sm text-neutral-900 focus:outline-none focus:ring-1 focus:ring-forest-emerald" value="Software"/>
          </div>
        </div>

        <div>
          <label class="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">Extraction Limit</label>
          <input id="twogis-cap" type="number" class="w-48 bg-neutral-50 border border-neutral-200 rounded-xl px-4 py-3 text-sm text-neutral-900 focus:outline-none focus:ring-1 focus:ring-forest-emerald" value="2000"/>
        </div>

        <button onclick="window.runTwoGis()" id="twogis-submit-btn" class="px-6 py-3.5 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-bold text-xs tracking-wide transition-all shadow-sm">
          Start 2GIS Scraper
        </button>
      </div>
    </div>

    <div id="tab-history" class="hidden space-y-5">
      <header>
        <h1 class="text-2xl font-bold tracking-tight text-neutral-900">Checkpoints & Session Vault</h1>
        <p class="text-xs text-neutral-500 mt-0.5">Instant one-click resume from any previously interrupted or completed run</p>
      </header>

      <div id="history-container" class="space-y-3">
        <div class="text-xs text-neutral-400">Loading ledger...</div>
      </div>
    </div>

    <div id="tab-developer" class="hidden space-y-5">
      <header>
        <h1 class="text-2xl font-bold tracking-tight text-neutral-900">Developer Dossier</h1>
        <p class="text-xs text-neutral-500 mt-0.5">Author architecture and technical registry</p>
      </header>

      <div class="bg-white rounded-[28px] p-7 border border-forest-cardBorder shadow-sm space-y-6">
        <div class="flex items-center gap-4">
          <div class="w-16 h-16 rounded-full overflow-hidden border-2 border-forest-emerald shadow-md flex-shrink-0">
            <img src="https://ik.imagekit.io/Reinhart/reinhart.png?updatedAt=1747593545727" class="w-full h-full object-cover"/>
          </div>
          <div>
            <h3 class="text-lg font-bold text-gray-900">Reinhart aka Kiri</h3>
            <p class="text-xs text-gray-500 font-medium">Lead Systems Architect & Core Developer</p>
            <p class="text-xs italic text-forest-emeraldDark font-semibold mt-1">"We do not do it because it's easy. We do it because we thought it would be easy."</p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <button onclick="window.pywebview.api.open_link('https://reinhart.pages.dev')" class="flex items-center justify-between p-3.5 rounded-2xl bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 transition-colors text-left">
            <div>
              <div class="text-xs font-bold text-gray-900">Portfolio Portal</div>
              <div class="text-[11px] text-gray-500">reinhart.pages.dev</div>
            </div>
            <span class="text-xs font-bold text-forest-emeraldDark">→</span>
          </button>
          <button onclick="window.pywebview.api.open_link('https://t.me/kiri0507')" class="flex items-center justify-between p-3.5 rounded-2xl bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 transition-colors text-left">
            <div>
              <div class="text-xs font-bold text-gray-900">Direct Wire (Telegram)</div>
              <div class="text-[11px] text-gray-500">@kiri0507</div>
            </div>
            <span class="text-xs font-bold text-sky-500">→</span>
          </button>
          <button onclick="window.pywebview.api.open_link('https://wa.me/13153701897')" class="flex items-center justify-between p-3.5 rounded-2xl bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 transition-colors text-left">
            <div>
              <div class="text-xs font-bold text-gray-900">WhatsApp Priority Line</div>
              <div class="text-[11px] text-gray-500">+1 (315) 370-1897</div>
            </div>
            <span class="text-xs font-bold text-emerald-600">→</span>
          </button>
          <button onclick="window.pywebview.api.open_link('https://github.com/Reinhart-py')" class="flex items-center justify-between p-3.5 rounded-2xl bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 transition-colors text-left">
            <div>
              <div class="text-xs font-bold text-gray-900">Source Repository (GitHub)</div>
              <div class="text-[11px] text-gray-500">Reinhart-py</div>
            </div>
            <span class="text-xs font-bold text-neutral-800">→</span>
          </button>
        </div>
      </div>
    </div>

  </div>
</main>

<script>
let currentTab = 'dashboard';
let totalLeadsCount = 0;
let totalSessionsCount = 0;

function switchTab(name) {
  currentTab = name;
  const tabs = ['dashboard', 'gmaps', 'twogis', 'history', 'developer'];
  tabs.forEach(t => {
    document.getElementById('tab-' + t).classList.add('hidden');
    const navBtn = document.getElementById('nav-' + t);
    navBtn.className = 'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-[#16221B] transition-all';
  });
  document.getElementById('tab-' + name).classList.remove('hidden');
  const activeNav = document.getElementById('nav-' + name);
  activeNav.className = 'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl bg-forest-activeNav text-white border border-[#26372D] shadow-sm transition-all';

  if (name === 'history') {
    renderHistory();
  }
}

function appendLog(line) {
  const stream = document.getElementById('console-stream');
  const row = document.createElement('div');
  row.className = 'leading-relaxed break-words';
  row.innerText = line;
  stream.appendChild(row);
  stream.scrollTop = stream.scrollHeight;

  if (line.includes('Extracted #') || line.includes('Saved #')) {
    totalLeadsCount++;
    document.getElementById('stat-total-leads').innerText = totalLeadsCount.toLocaleString();
  }
}

async function submitAuth() {
  const keyInput = document.getElementById('auth-key-input');
  const errDiv = document.getElementById('auth-error');
  const submitBtn = document.getElementById('auth-submit-btn');

  const key = keyInput.value.trim();
  if (!key) return;

  errDiv.innerText = '';
  submitBtn.disabled = true;
  submitBtn.innerText = 'Validating...';

  const res = await window.pywebview.api.verify_license(key);
  submitBtn.disabled = false;
  submitBtn.innerText = 'Activate';

  if (res.passed) {
    unlockUI(res);
  } else {
    errDiv.innerText = res.msg || 'License rejected.';
  }
}

function unlockUI(data) {
  document.getElementById('view-auth').classList.add('hidden');
  document.getElementById('view-app').classList.remove('hidden');

  document.getElementById('sidebar-owner-name').innerText = data.owner || 'Active Node';
  document.getElementById('sidebar-expiry-text').innerText = data.expires || 'Valid';
  document.getElementById('stat-owner-text').innerText = 'Licensed to: ' + (data.owner || 'Subscriber');
  document.getElementById('stat-expiry-text').innerText = data.expires || 'Permanent';

  checkActiveRecovery();
  loadStats();
}

async function checkActiveRecovery() {
  const active = await window.pywebview.api.get_active_checkpoint();
  if (active && active.target) {
    const banner = document.getElementById('recovery-banner');
    document.getElementById('recovery-banner-text').innerText = `[${(active.engine||'SYS').toUpperCase()}] ${active.target} at step ${active.last_step}`;
    banner.classList.remove('hidden');
  }
}

async function loadStats() {
  const history = await window.pywebview.api.get_history();
  totalSessionsCount = history.length;
  document.getElementById('stat-total-sessions').innerText = totalSessionsCount;
  totalLeadsCount = history.reduce((acc, curr) => acc + (curr.total_saved || 0), 0);
  document.getElementById('stat-total-leads').innerText = totalLeadsCount.toLocaleString();
}

async function renderHistory() {
  const container = document.getElementById('history-container');
  container.innerHTML = '<div class="text-xs text-neutral-400">Loading history ledger...</div>';

  const history = await window.pywebview.api.get_history();
  if (!history || history.length === 0) {
    container.innerHTML = '<div class="text-xs text-neutral-400 p-4 bg-white rounded-2xl border border-forest-cardBorder">No checkpoints recorded yet.</div>';
    return;
  }

  container.innerHTML = '';
  history.forEach(item => {
    const card = document.createElement('div');
    card.className = 'bg-white rounded-2xl p-4 border border-forest-cardBorder shadow-sm flex items-center justify-between';
    card.innerHTML = `
      <div>
        <div class="flex items-center gap-2">
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-forest-sidebar text-white uppercase">${item.engine || 'SYS'}</span>
          <h4 class="text-xs font-bold text-gray-900 truncate max-w-xs sm:max-w-md">${item.target || 'Search Task'}</h4>
        </div>
        <p class="text-[11px] text-gray-500 mt-1">Saved: <b class="text-gray-900">${item.total_saved || 0}</b> leads | Resumes at Step: <b class="text-gray-900">${item.last_step || 1}</b></p>
      </div>
      <button onclick='window.resumeHistorical(${JSON.stringify(item)})' class="px-4 py-2 rounded-xl bg-forest-sidebar hover:bg-[#1B2821] text-white font-bold text-xs transition-all">
        Resume
      </button>
    `;
    container.appendChild(card);
  });
}

async function resumeHistorical(item) {
  switchTab('dashboard');
  appendLog(`Resuming [${(item.engine||'').toUpperCase()}] task: ${item.target} from step ${item.last_step}...`);
  await window.pywebview.api.resume_checkpoint(item);
}

async function resumeActiveCheckpoint() {
  document.getElementById('recovery-banner').classList.add('hidden');
  const active = await window.pywebview.api.get_active_checkpoint();
  if (active) {
    await resumeHistorical(active);
  }
}

async function dismissActiveCheckpoint() {
  document.getElementById('recovery-banner').classList.add('hidden');
  await window.pywebview.api.dismiss_checkpoint();
  appendLog('Pending checkpoint dismissed.');
}

async function selectBatchFile() {
  const path = await window.pywebview.api.browse_file();
  if (path) {
    document.getElementById('gmaps-input').value = path;
  }
}

async function runGmaps() {
  const target = document.getElementById('gmaps-input').value.trim();
  const cap = parseInt(document.getElementById('gmaps-cap').value.trim()) || 0;
  if (!target) return;

  switchTab('dashboard');
  appendLog(`Starting Google Maps extraction for: ${target}`);
  await window.pywebview.api.start_gmaps(target, cap);
}

async function runTwoGis() {
  const city = document.getElementById('twogis-city').value.trim();
  const query = document.getElementById('twogis-query').value.trim();
  const cap = parseInt(document.getElementById('twogis-cap').value.trim()) || 0;
  if (!city || !query) return;

  switchTab('dashboard');
  appendLog(`Starting 2GIS extraction for: ${city} -> ${query}`);
  await window.pywebview.api.start_twogis(city, query, cap);
}

async function logoutLicense() {
  await window.pywebview.api.purge_license();
  document.getElementById('view-app').classList.add('hidden');
  document.getElementById('view-auth').classList.remove('hidden');
  document.getElementById('auth-key-input').value = '';
}

window.addEventListener('pywebviewready', async () => {
  const savedRes = await window.pywebview.api.check_saved_license();
  if (savedRes && savedRes.passed) {
    unlockUI(savedRes);
  }
});
</script>
</body>
</html>
"""

class JiyaBridge:
    def __init__(self):
        self.window = None
        self.is_running = False

    def set_window(self, win):
        self.window = win

    def open_link(self, url: str) -> None:
        webbrowser.open(url)

    def verify_license(self, key: str) -> Dict[str, Any]:
        res = verify_key_payload(key)
        if res.get("passed"):
            save_key(key)
        return res

    def check_saved_license(self) -> Dict[str, Any]:
        key = get_saved_key()
        if not key:
            return {"passed": False}
        return verify_key_payload(key)

    def purge_license(self) -> None:
        revoke_saved_key()

    def get_history(self) -> List[Dict[str, Any]]:
        return load_all_history()

    def get_active_checkpoint(self) -> Any:
        return get_active_checkpoint()

    def dismiss_checkpoint(self) -> None:
        clear_active_checkpoint()

    def browse_file(self) -> str:
        if not self.window:
            return ""
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Supported Datasets (*.csv;*.xlsx;*.txt)", "All Files (*.*)")
        )
        return result[0] if result else ""

    def log_stream(self, text: str) -> None:
        if self.window:
            safe_text = json.dumps(str(text))
            self.window.evaluate_js(f"appendLog({safe_text});")

    def start_gmaps(self, target: str, cap: int, start_idx: int = 0) -> None:
        if self.is_running:
            return
        self.is_running = True

        out_path = str(get_export_dir() / "gmaps_extracted_leads.csv")

        def worker():
            runner = GMapsRunner(
                target_input=target,
                output_path=out_path,
                start_index=start_idx,
                target_count=cap,
                ui_logger=self.log_stream
            )
            try:
                runner.run()
            finally:
                self.is_running = False
                self.log_stream("Google Maps extraction completed.")

        threading.Thread(target=worker, daemon=True).start()

    def start_twogis(self, city: str, query: str, cap: int, start_page: int = 1, initial_saved: int = 0) -> None:
        if self.is_running:
            return
        self.is_running = True

        out_path = str(get_export_dir() / "2gis_extracted_leads.csv")

        def worker():
            class Config:
                engine = "2gis"
                city_name = city
                query_string = query
                country = "ae"
                output_path = out_path
                start_page = start_page
                initial_saved = initial_saved
                target_count = cap

            runner = TwoGISRunner(config=Config(), ui_logger=self.log_stream)
            try:
                runner.run()
            finally:
                self.is_running = False
                self.log_stream("2GIS regional extraction completed.")

        threading.Thread(target=worker, daemon=True).start()

    def resume_checkpoint(self, item: Dict[str, Any]) -> None:
        engine = item.get("engine")
        if engine == "gmaps":
            target = item.get("target", "")
            cap = int(item.get("target_count", 0))
            start_idx = int(item.get("last_step", 0))
            self.start_gmaps(target, cap, start_idx)
        elif engine == "2gis":
            city = item.get("city_name", "dubai")
            query = item.get("query_string", "")
            cap = int(item.get("target_count", 0))
            start_page = int(item.get("last_step", 1))
            initial_saved = int(item.get("total_saved", 0))
            self.start_twogis(city, query, cap, start_page, initial_saved)

class KiriApp:
    def __init__(self):
        self.bridge = JiyaBridge()
        self.window = webview.create_window(
            title="Kiri",
            html=HTML_UI,
            js_api=self.bridge,
            width=1240,
            height=820,
            min_size=(960, 640),
            background_color="#0B2416"
        )
        self.bridge.set_window(self.window)

    def mainloop(self):
        webview.start(debug=False)
