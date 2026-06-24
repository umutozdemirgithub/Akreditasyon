from __future__ import annotations

import json
from typing import Any

from .db import get_conn, now_iso, rows_to_dicts, transaction
from .tenancy import DEFAULT_TENANT_ID, list_tenants_admin, user_tenant_id
from .repositories import get_user, is_super_admin_user, log_activity

APPEARANCE_PACKAGES: list[dict[str, Any]] = [
    {
        "id": "corporate_blue",
        "name": "Kurumsal Mavi",
        "description": "Klasik akreditasyon görünümü; mavi sidebar, açık çalışma alanı.",
        "category": "Kurumsal",
        "mode": "light",
        "density": "comfort",
        "accent": "#2563eb",
        "sidebar": "#0d2b68",
        "preview": "Mavi / Beyaz"
    },
    {
        "id": "executive_navy",
        "name": "Executive Lacivert",
        "description": "Üst yönetim ve denetim ekranları için koyu lacivert premium görünüm.",
        "category": "Premium",
        "mode": "dark",
        "density": "comfort",
        "accent": "#60a5fa",
        "sidebar": "#081426",
        "preview": "Lacivert / Buz Mavi"
    },
    {
        "id": "emerald_quality",
        "name": "Zümrüt Kalite",
        "description": "Kalite yönetimi ve sürekli iyileştirme vurgusu için yeşil tonlu paket.",
        "category": "Kalite",
        "mode": "light",
        "density": "comfort",
        "accent": "#059669",
        "sidebar": "#064e3b",
        "preview": "Zümrüt / Açık Yeşil"
    },
    {
        "id": "health_teal",
        "name": "Sağlık MYO Turkuaz",
        "description": "Sağlık hizmetleri MYO ve klinik programlar için temiz turkuaz görünüm.",
        "category": "Alan Odaklı",
        "mode": "light",
        "density": "comfort",
        "accent": "#0f766e",
        "sidebar": "#134e4a",
        "preview": "Turkuaz / Beyaz"
    },
    {
        "id": "engineering_indigo",
        "name": "Mühendislik Indigo",
        "description": "Mühendislik ve teknik programlar için indigo/mavi teknoloji görünümü.",
        "category": "Alan Odaklı",
        "mode": "light",
        "density": "compact",
        "accent": "#4f46e5",
        "sidebar": "#1e1b4b",
        "preview": "Indigo / Açık Gri"
    },
    {
        "id": "education_sky",
        "name": "Eğitim Fakültesi Sky",
        "description": "Eğitim fakültesi ve pedagojik programlar için ferah açık mavi paket.",
        "category": "Alan Odaklı",
        "mode": "light",
        "density": "spacious",
        "accent": "#0284c7",
        "sidebar": "#075985",
        "preview": "Sky / Beyaz"
    },
    {
        "id": "burgundy_accreditation",
        "name": "Bordo Akreditasyon",
        "description": "Resmî kurul, senato ve denetim sunumları için bordo vurgu.",
        "category": "Resmî",
        "mode": "light",
        "density": "comfort",
        "accent": "#be123c",
        "sidebar": "#4c0519",
        "preview": "Bordo / Krem"
    },
    {
        "id": "violet_modern",
        "name": "Modern Mor",
        "description": "Modern kurum portali hissi için mor-violet geçişli görünüm.",
        "category": "Modern",
        "mode": "dark",
        "density": "comfort",
        "accent": "#8b5cf6",
        "sidebar": "#2e1065",
        "preview": "Mor / Gece"
    },
    {
        "id": "amber_focus",
        "name": "Amber Odak",
        "description": "Geciken işler, risk takibi ve operasyon ekipleri için sıcak amber paket.",
        "category": "Operasyon",
        "mode": "light",
        "density": "compact",
        "accent": "#d97706",
        "sidebar": "#78350f",
        "preview": "Amber / Beyaz"
    },
    {
        "id": "graphite_minimal",
        "name": "Grafit Minimal",
        "description": "Sade, minimal ve düşük dikkat dağıtan gri/grafit görünüm.",
        "category": "Minimal",
        "mode": "light",
        "density": "comfort",
        "accent": "#475569",
        "sidebar": "#111827",
        "preview": "Grafit / Gri"
    },
    {
        "id": "high_contrast",
        "name": "Yüksek Kontrast",
        "description": "Projeksiyon, düşük görüş veya yüksek okunabilirlik ihtiyacı için kontrastlı paket.",
        "category": "Erişilebilirlik",
        "mode": "dark",
        "density": "spacious",
        "accent": "#facc15",
        "sidebar": "#000000",
        "preview": "Siyah / Sarı"
    },
    {
        "id": "rose_dusk",
        "name": "Gül Alacakaranlığı",
        "description": "Yumuşak pembe ve mürdüm tonlarıyla sakin premium görünüm.",
        "category": "Premium",
        "mode": "light",
        "density": "comfort",
        "accent": "#e11d48",
        "sidebar": "#4a0d2d",
        "preview": "Gül / Beyaz"
    },
    {
        "id": "mint_glass",
        "name": "Mint Glass",
        "description": "Cam etkili yüzeylerle serin ve ferah bir mint teması.",
        "category": "Modern",
        "mode": "light",
        "density": "spacious",
        "accent": "#10b981",
        "sidebar": "#0f3d34",
        "preview": "Mint / Cam"
    },
    {
        "id": "arctic_frost",
        "name": "Arctic Frost",
        "description": "Açık buz mavisi tonlarıyla sakin ve temiz çalışma alanı.",
        "category": "Minimal",
        "mode": "light",
        "density": "spacious",
        "accent": "#3b82f6",
        "sidebar": "#164e63",
        "preview": "Buz / Beyaz"
    },
    {
        "id": "sunset_coral",
        "name": "Sunset Coral",
        "description": "Sıcak mercan vurgulu enerjik ve davetkâr arayüz.",
        "category": "Modern",
        "mode": "light",
        "density": "comfort",
        "accent": "#f97316",
        "sidebar": "#7c2d12",
        "preview": "Mercan / Krem"
    },
    {
        "id": "forest_ink",
        "name": "Forest Ink",
        "description": "Koyu yeşil ve mürekkep tonlarıyla ciddi ve odaklı görünüm.",
        "category": "Kurumsal",
        "mode": "dark",
        "density": "comfort",
        "accent": "#22c55e",
        "sidebar": "#052e16",
        "preview": "Orman / Gece"
    },
    {
        "id": "slate_orchid",
        "name": "Slate Orchid",
        "description": "Slate ve orkide tonlarıyla dengeli modern tema.",
        "category": "Modern",
        "mode": "dark",
        "density": "comfort",
        "accent": "#a855f7",
        "sidebar": "#1e1b4b",
        "preview": "Orkide / Slate"
    },
    {
        "id": "terracotta_warm",
        "name": "Terracotta Warm",
        "description": "Toprak tonlarıyla sıcak ve insani bir görünüm.",
        "category": "Alan Odaklı",
        "mode": "light",
        "density": "comfort",
        "accent": "#c2410c",
        "sidebar": "#7c2d12",
        "preview": "Toprak / Krem"
    },
    {
        "id": "oceanic_aqua",
        "name": "Oceanic Aqua",
        "description": "Aqua ve deniz tonlarıyla canlı, temiz bir tema.",
        "category": "Alan Odaklı",
        "mode": "light",
        "density": "compact",
        "accent": "#0891b2",
        "sidebar": "#0c4a6e",
        "preview": "Aqua / Beyaz"
    },
    {
        "id": "cherry_blush",
        "name": "Cherry Blush",
        "description": "Açık kiraz tonlarıyla yumuşak ve premium hissiyat.",
        "category": "Premium",
        "mode": "light",
        "density": "spacious",
        "accent": "#db2777",
        "sidebar": "#831843",
        "preview": "Kiraz / Pembe"
    },
    {
        "id": "midnight_teal",
        "name": "Midnight Teal",
        "description": "Gece mavisi ve teal karışımıyla derin odak görünümü.",
        "category": "Premium",
        "mode": "dark",
        "density": "compact",
        "accent": "#14b8a6",
        "sidebar": "#042f2e",
        "preview": "Gece / Teal"
    },
    {
        "id": "royal_plum",
        "name": "Royal Plum",
        "description": "Kraliyet moru ile güçlü ve elit bir görünüm.",
        "category": "Resmî",
        "mode": "dark",
        "density": "comfort",
        "accent": "#c084fc",
        "sidebar": "#3b0764",
        "preview": "Mor / Gümüş"
    },
    {
        "id": "sandstone_soft",
        "name": "Sandstone Soft",
        "description": "Yumuşak taş tonlarıyla sakin ve okunaklı arayüz.",
        "category": "Minimal",
        "mode": "light",
        "density": "comfort",
        "accent": "#b45309",
        "sidebar": "#57534e",
        "preview": "Taş / Kum"
    },
    {
        "id": "lime_matrix",
        "name": "Lime Matrix",
        "description": "Canlı lime vurgulu yüksek fark edilir operasyon teması.",
        "category": "Operasyon",
        "mode": "dark",
        "density": "compact",
        "accent": "#84cc16",
        "sidebar": "#1a2e05",
        "preview": "Lime / Koyu"
    },
    {
        "id": "cobalt_ice",
        "name": "Cobalt Ice",
        "description": "Kobalt vurgular ve buz beyazı yüzeylerle teknik görünüm.",
        "category": "Alan Odaklı",
        "mode": "light",
        "density": "compact",
        "accent": "#1d4ed8",
        "sidebar": "#172554",
        "preview": "Kobalt / Buz"
    },
    {
        "id": "pearl_gray",
        "name": "Pearl Gray",
        "description": "Nötr gri tonlar ve yüksek sadelik sunan kurumsal tema.",
        "category": "Kurumsal",
        "mode": "light",
        "density": "comfort",
        "accent": "#6b7280",
        "sidebar": "#374151",
        "preview": "İnci Gri"
    },
    {
        "id": "cyber_green",
        "name": "Cyber Green",
        "description": "Siber yeşil ile analitik ve teknoloji hissi veren koyu tema.",
        "category": "Modern",
        "mode": "dark",
        "density": "compact",
        "accent": "#22c55e",
        "sidebar": "#031b11",
        "preview": "Siber / Koyu"
    },
    {
        "id": "rose_gold",
        "name": "Rose Gold",
        "description": "Rose gold ve krem tonlarıyla premium yönetici teması.",
        "category": "Premium",
        "mode": "light",
        "density": "spacious",
        "accent": "#d97786",
        "sidebar": "#7c2d4d",
        "preview": "Rose Gold"
    },
    {
        "id": "aurora_purple",
        "name": "Aurora Purple",
        "description": "Aurora hissi veren mor-mavi geçişli gösterişli tema.",
        "category": "Modern",
        "mode": "dark",
        "density": "spacious",
        "accent": "#7c3aed",
        "sidebar": "#1e1b4b",
        "preview": "Aurora / Mor"
    },
    {
        "id": "denim_light",
        "name": "Denim Light",
        "description": "Denim mavisi ve yumuşak yüzeylerle dengeli kullanım teması.",
        "category": "Kurumsal",
        "mode": "light",
        "density": "comfort",
        "accent": "#2563eb",
        "sidebar": "#1e3a8a",
        "preview": "Denim / Açık"
    },
    {
        "id": "obsidian_red",
        "name": "Obsidian Red",
        "description": "Siyah-kırmızı kontrastıyla güçlü denetim ve uyarı görünümü.",
        "category": "Operasyon",
        "mode": "dark",
        "density": "comfort",
        "accent": "#ef4444",
        "sidebar": "#0f172a",
        "preview": "Obsidyen / Kırmızı"
    }
]

PACKAGE_MAP = {row["id"]: row for row in APPEARANCE_PACKAGES}
DEFAULT_APPEARANCE_PACKAGE = "corporate_blue"


THEME_TOKEN_OVERRIDES: dict[str, dict[str, str]] = {
    "corporate_blue": {
        "accent": "#2563eb",
        "accent_2": "#38bdf8",
        "accent_soft": "#dbeafe",
        "accent_strong": "#1d4ed8",
        "sidebar_bg": "#0d2b68",
        "sidebar_bg_2": "#061a3d",
        "sidebar_text": "#ffffff",
        "sidebar_muted": "#b7c9ea",
        "workspace_bg": "#eef6ff",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f8fbff",
        "text_primary": "#142037",
        "text_secondary": "#526985",
        "border": "#d7e3f1",
        "hero_from": "#0d2b68",
        "hero_to": "#2563eb",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#dc2626"
    },
    "executive_navy": {
        "accent": "#60a5fa",
        "accent_2": "#a78bfa",
        "accent_soft": "#1e3a5f",
        "accent_strong": "#93c5fd",
        "sidebar_bg": "#081426",
        "sidebar_bg_2": "#020617",
        "sidebar_text": "#f8fafc",
        "sidebar_muted": "#9fb4d0",
        "workspace_bg": "#0b1220",
        "card_bg": "#111c2f",
        "card_bg_soft": "#16233a",
        "text_primary": "#f8fafc",
        "text_secondary": "#bfd0e8",
        "border": "#26364f",
        "hero_from": "#020617",
        "hero_to": "#1d4ed8",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#fb7185"
    },
    "emerald_quality": {
        "accent": "#059669",
        "accent_2": "#22c55e",
        "accent_soft": "#dcfce7",
        "accent_strong": "#047857",
        "sidebar_bg": "#064e3b",
        "sidebar_bg_2": "#022c22",
        "sidebar_text": "#ecfdf5",
        "sidebar_muted": "#a7f3d0",
        "workspace_bg": "#eefdf6",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f0fdf4",
        "text_primary": "#12352d",
        "text_secondary": "#4f6f64",
        "border": "#cdeedc",
        "hero_from": "#064e3b",
        "hero_to": "#059669",
        "success": "#16a34a",
        "warning": "#ca8a04",
        "danger": "#dc2626"
    },
    "health_teal": {
        "accent": "#0f766e",
        "accent_2": "#06b6d4",
        "accent_soft": "#ccfbf1",
        "accent_strong": "#115e59",
        "sidebar_bg": "#134e4a",
        "sidebar_bg_2": "#042f2e",
        "sidebar_text": "#f0fdfa",
        "sidebar_muted": "#99f6e4",
        "workspace_bg": "#ecfeff",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f0fdfa",
        "text_primary": "#123b3a",
        "text_secondary": "#52706c",
        "border": "#c7ece8",
        "hero_from": "#134e4a",
        "hero_to": "#0f766e",
        "success": "#10b981",
        "warning": "#d97706",
        "danger": "#e11d48"
    },
    "engineering_indigo": {
        "accent": "#4f46e5",
        "accent_2": "#06b6d4",
        "accent_soft": "#e0e7ff",
        "accent_strong": "#3730a3",
        "sidebar_bg": "#1e1b4b",
        "sidebar_bg_2": "#11102f",
        "sidebar_text": "#eef2ff",
        "sidebar_muted": "#c4c7ff",
        "workspace_bg": "#f5f7ff",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f8faff",
        "text_primary": "#171936",
        "text_secondary": "#59627c",
        "border": "#dbe2ff",
        "hero_from": "#1e1b4b",
        "hero_to": "#4f46e5",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#ef4444"
    },
    "education_sky": {
        "accent": "#0284c7",
        "accent_2": "#22d3ee",
        "accent_soft": "#e0f2fe",
        "accent_strong": "#0369a1",
        "sidebar_bg": "#075985",
        "sidebar_bg_2": "#0c4a6e",
        "sidebar_text": "#f0f9ff",
        "sidebar_muted": "#bae6fd",
        "workspace_bg": "#f0f9ff",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f8fcff",
        "text_primary": "#123047",
        "text_secondary": "#526a7d",
        "border": "#cfe9fa",
        "hero_from": "#075985",
        "hero_to": "#0284c7",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#dc2626"
    },
    "burgundy_accreditation": {
        "accent": "#be123c",
        "accent_2": "#f97316",
        "accent_soft": "#ffe4e6",
        "accent_strong": "#9f1239",
        "sidebar_bg": "#4c0519",
        "sidebar_bg_2": "#26030d",
        "sidebar_text": "#fff1f2",
        "sidebar_muted": "#fecdd3",
        "workspace_bg": "#fff7ed",
        "card_bg": "#fffdfb",
        "card_bg_soft": "#fff1f2",
        "text_primary": "#3f1722",
        "text_secondary": "#76515a",
        "border": "#f4d2d8",
        "hero_from": "#4c0519",
        "hero_to": "#be123c",
        "success": "#16a34a",
        "warning": "#f59e0b",
        "danger": "#dc2626"
    },
    "violet_modern": {
        "accent": "#8b5cf6",
        "accent_2": "#ec4899",
        "accent_soft": "#2e1a57",
        "accent_strong": "#c4b5fd",
        "sidebar_bg": "#2e1065",
        "sidebar_bg_2": "#16072f",
        "sidebar_text": "#faf5ff",
        "sidebar_muted": "#ddd6fe",
        "workspace_bg": "#121024",
        "card_bg": "#1d1733",
        "card_bg_soft": "#251d44",
        "text_primary": "#faf5ff",
        "text_secondary": "#d7cdf8",
        "border": "#3b2d63",
        "hero_from": "#16072f",
        "hero_to": "#7c3aed",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#fb7185"
    },
    "amber_focus": {
        "accent": "#d97706",
        "accent_2": "#facc15",
        "accent_soft": "#fef3c7",
        "accent_strong": "#b45309",
        "sidebar_bg": "#78350f",
        "sidebar_bg_2": "#451a03",
        "sidebar_text": "#fffbeb",
        "sidebar_muted": "#fde68a",
        "workspace_bg": "#fff8eb",
        "card_bg": "#ffffff",
        "card_bg_soft": "#fffbeb",
        "text_primary": "#3b2711",
        "text_secondary": "#735b3c",
        "border": "#f5dfb8",
        "hero_from": "#78350f",
        "hero_to": "#d97706",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#dc2626"
    },
    "graphite_minimal": {
        "accent": "#475569",
        "accent_2": "#94a3b8",
        "accent_soft": "#e2e8f0",
        "accent_strong": "#334155",
        "sidebar_bg": "#111827",
        "sidebar_bg_2": "#030712",
        "sidebar_text": "#f8fafc",
        "sidebar_muted": "#cbd5e1",
        "workspace_bg": "#f1f5f9",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f8fafc",
        "text_primary": "#111827",
        "text_secondary": "#64748b",
        "border": "#d6dee9",
        "hero_from": "#111827",
        "hero_to": "#475569",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#dc2626"
    },
    "high_contrast": {
        "accent": "#facc15",
        "accent_2": "#ffffff",
        "accent_soft": "#312e04",
        "accent_strong": "#fde047",
        "sidebar_bg": "#000000",
        "sidebar_bg_2": "#020617",
        "sidebar_text": "#ffffff",
        "sidebar_muted": "#fef08a",
        "workspace_bg": "#020617",
        "card_bg": "#0f172a",
        "card_bg_soft": "#111827",
        "text_primary": "#ffffff",
        "text_secondary": "#e5e7eb",
        "border": "#facc15",
        "hero_from": "#000000",
        "hero_to": "#4a4004",
        "success": "#22c55e",
        "warning": "#facc15",
        "danger": "#fb7185"
    },
    "rose_dusk": {
        "accent": "#e11d48",
        "accent_2": "#f472b6",
        "accent_soft": "#ffe4e6",
        "accent_strong": "#be123c",
        "sidebar_bg": "#4a0d2d",
        "sidebar_bg_2": "#2f0a1c",
        "sidebar_text": "#fff7fb",
        "sidebar_muted": "#fecdd3",
        "workspace_bg": "#fff7fb",
        "card_bg": "#ffffff",
        "card_bg_soft": "#fff1f7",
        "text_primary": "#3f1729",
        "text_secondary": "#7f5266",
        "border": "#f5d1df",
        "hero_from": "#4a0d2d",
        "hero_to": "#e11d48",
        "success": "#16a34a",
        "warning": "#f59e0b",
        "danger": "#e11d48"
    },
    "mint_glass": {
        "accent": "#10b981",
        "accent_2": "#2dd4bf",
        "accent_soft": "#d1fae5",
        "accent_strong": "#059669",
        "sidebar_bg": "#0f3d34",
        "sidebar_bg_2": "#082721",
        "sidebar_text": "#ecfdf5",
        "sidebar_muted": "#99f6e4",
        "workspace_bg": "#effcf7",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f4fffb",
        "text_primary": "#12352d",
        "text_secondary": "#53716b",
        "border": "#cdeedc",
        "hero_from": "#0f3d34",
        "hero_to": "#10b981",
        "success": "#10b981",
        "warning": "#d97706",
        "danger": "#dc2626"
    },
    "arctic_frost": {
        "accent": "#3b82f6",
        "accent_2": "#7dd3fc",
        "accent_soft": "#e0f2fe",
        "accent_strong": "#1d4ed8",
        "sidebar_bg": "#164e63",
        "sidebar_bg_2": "#083344",
        "sidebar_text": "#ecfeff",
        "sidebar_muted": "#bae6fd",
        "workspace_bg": "#f4fbff",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f3fbff",
        "text_primary": "#143247",
        "text_secondary": "#5b7386",
        "border": "#d4ebf8",
        "hero_from": "#164e63",
        "hero_to": "#3b82f6",
        "success": "#16a34a",
        "warning": "#f59e0b",
        "danger": "#ef4444"
    },
    "sunset_coral": {
        "accent": "#f97316",
        "accent_2": "#fb7185",
        "accent_soft": "#ffedd5",
        "accent_strong": "#ea580c",
        "sidebar_bg": "#7c2d12",
        "sidebar_bg_2": "#431407",
        "sidebar_text": "#fff7ed",
        "sidebar_muted": "#fdba74",
        "workspace_bg": "#fff7ed",
        "card_bg": "#fffdfb",
        "card_bg_soft": "#fff1e8",
        "text_primary": "#45210d",
        "text_secondary": "#7f5b49",
        "border": "#f7dac9",
        "hero_from": "#7c2d12",
        "hero_to": "#f97316",
        "success": "#16a34a",
        "warning": "#ea580c",
        "danger": "#dc2626"
    },
    "forest_ink": {
        "accent": "#22c55e",
        "accent_2": "#4ade80",
        "accent_soft": "#133227",
        "accent_strong": "#86efac",
        "sidebar_bg": "#052e16",
        "sidebar_bg_2": "#02170b",
        "sidebar_text": "#f0fdf4",
        "sidebar_muted": "#bbf7d0",
        "workspace_bg": "#0d1f15",
        "card_bg": "#11251a",
        "card_bg_soft": "#163124",
        "text_primary": "#f0fdf4",
        "text_secondary": "#bbd7c6",
        "border": "#28533c",
        "hero_from": "#052e16",
        "hero_to": "#166534",
        "success": "#22c55e",
        "warning": "#fbbf24",
        "danger": "#fb7185"
    },
    "slate_orchid": {
        "accent": "#a855f7",
        "accent_2": "#818cf8",
        "accent_soft": "#261c4d",
        "accent_strong": "#ddd6fe",
        "sidebar_bg": "#1e1b4b",
        "sidebar_bg_2": "#0f1028",
        "sidebar_text": "#f5f3ff",
        "sidebar_muted": "#ddd6fe",
        "workspace_bg": "#141628",
        "card_bg": "#1e2239",
        "card_bg_soft": "#252b47",
        "text_primary": "#f8faff",
        "text_secondary": "#c6ceea",
        "border": "#3c4572",
        "hero_from": "#1e1b4b",
        "hero_to": "#9333ea",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#fb7185"
    },
    "terracotta_warm": {
        "accent": "#c2410c",
        "accent_2": "#fb923c",
        "accent_soft": "#ffedd5",
        "accent_strong": "#9a3412",
        "sidebar_bg": "#7c2d12",
        "sidebar_bg_2": "#4b190b",
        "sidebar_text": "#fff7ed",
        "sidebar_muted": "#fdba74",
        "workspace_bg": "#fff7f0",
        "card_bg": "#ffffff",
        "card_bg_soft": "#fff1e8",
        "text_primary": "#44251a",
        "text_secondary": "#7c6157",
        "border": "#f1d8ca",
        "hero_from": "#7c2d12",
        "hero_to": "#c2410c",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#dc2626"
    },
    "oceanic_aqua": {
        "accent": "#0891b2",
        "accent_2": "#22d3ee",
        "accent_soft": "#cffafe",
        "accent_strong": "#0e7490",
        "sidebar_bg": "#0c4a6e",
        "sidebar_bg_2": "#082f49",
        "sidebar_text": "#ecfeff",
        "sidebar_muted": "#a5f3fc",
        "workspace_bg": "#ecfdff",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f0feff",
        "text_primary": "#143447",
        "text_secondary": "#577183",
        "border": "#cdebf5",
        "hero_from": "#0c4a6e",
        "hero_to": "#0891b2",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#e11d48"
    },
    "cherry_blush": {
        "accent": "#db2777",
        "accent_2": "#f472b6",
        "accent_soft": "#fce7f3",
        "accent_strong": "#be185d",
        "sidebar_bg": "#831843",
        "sidebar_bg_2": "#4a0c26",
        "sidebar_text": "#fff7fb",
        "sidebar_muted": "#fbcfe8",
        "workspace_bg": "#fff7fb",
        "card_bg": "#ffffff",
        "card_bg_soft": "#fff1f6",
        "text_primary": "#45182c",
        "text_secondary": "#7d5a69",
        "border": "#f2d7e5",
        "hero_from": "#831843",
        "hero_to": "#db2777",
        "success": "#16a34a",
        "warning": "#f59e0b",
        "danger": "#db2777"
    },
    "midnight_teal": {
        "accent": "#14b8a6",
        "accent_2": "#67e8f9",
        "accent_soft": "#173a40",
        "accent_strong": "#99f6e4",
        "sidebar_bg": "#042f2e",
        "sidebar_bg_2": "#021716",
        "sidebar_text": "#ecfeff",
        "sidebar_muted": "#99f6e4",
        "workspace_bg": "#091818",
        "card_bg": "#112225",
        "card_bg_soft": "#173036",
        "text_primary": "#f0fdfa",
        "text_secondary": "#bdd8d8",
        "border": "#2a4b4c",
        "hero_from": "#042f2e",
        "hero_to": "#0f766e",
        "success": "#2dd4bf",
        "warning": "#fbbf24",
        "danger": "#fb7185"
    },
    "royal_plum": {
        "accent": "#c084fc",
        "accent_2": "#e879f9",
        "accent_soft": "#35104f",
        "accent_strong": "#e9d5ff",
        "sidebar_bg": "#3b0764",
        "sidebar_bg_2": "#22043a",
        "sidebar_text": "#faf5ff",
        "sidebar_muted": "#e9d5ff",
        "workspace_bg": "#130c1f",
        "card_bg": "#1f1630",
        "card_bg_soft": "#281d3f",
        "text_primary": "#faf5ff",
        "text_secondary": "#d6c8ec",
        "border": "#47345f",
        "hero_from": "#3b0764",
        "hero_to": "#a855f7",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#fb7185"
    },
    "sandstone_soft": {
        "accent": "#b45309",
        "accent_2": "#f59e0b",
        "accent_soft": "#fef3c7",
        "accent_strong": "#92400e",
        "sidebar_bg": "#57534e",
        "sidebar_bg_2": "#44403c",
        "sidebar_text": "#fafaf9",
        "sidebar_muted": "#e7e5e4",
        "workspace_bg": "#faf8f3",
        "card_bg": "#ffffff",
        "card_bg_soft": "#fffcf5",
        "text_primary": "#292524",
        "text_secondary": "#68635e",
        "border": "#e5ddd0",
        "hero_from": "#57534e",
        "hero_to": "#b45309",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#dc2626"
    },
    "lime_matrix": {
        "accent": "#84cc16",
        "accent_2": "#bef264",
        "accent_soft": "#20310c",
        "accent_strong": "#d9f99d",
        "sidebar_bg": "#1a2e05",
        "sidebar_bg_2": "#101d03",
        "sidebar_text": "#f7fee7",
        "sidebar_muted": "#d9f99d",
        "workspace_bg": "#11170a",
        "card_bg": "#1a2411",
        "card_bg_soft": "#202c15",
        "text_primary": "#f7fee7",
        "text_secondary": "#d1e4b0",
        "border": "#385323",
        "hero_from": "#1a2e05",
        "hero_to": "#65a30d",
        "success": "#84cc16",
        "warning": "#fbbf24",
        "danger": "#fb7185"
    },
    "cobalt_ice": {
        "accent": "#1d4ed8",
        "accent_2": "#60a5fa",
        "accent_soft": "#dbeafe",
        "accent_strong": "#1e40af",
        "sidebar_bg": "#172554",
        "sidebar_bg_2": "#0f1638",
        "sidebar_text": "#eff6ff",
        "sidebar_muted": "#bfdbfe",
        "workspace_bg": "#f4f8ff",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f6f9ff",
        "text_primary": "#17203c",
        "text_secondary": "#5e6c8f",
        "border": "#d7e2fb",
        "hero_from": "#172554",
        "hero_to": "#1d4ed8",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#ef4444"
    },
    "pearl_gray": {
        "accent": "#6b7280",
        "accent_2": "#cbd5e1",
        "accent_soft": "#eef2f7",
        "accent_strong": "#4b5563",
        "sidebar_bg": "#374151",
        "sidebar_bg_2": "#1f2937",
        "sidebar_text": "#f9fafb",
        "sidebar_muted": "#d1d5db",
        "workspace_bg": "#f7f8fa",
        "card_bg": "#ffffff",
        "card_bg_soft": "#fafbfc",
        "text_primary": "#1f2937",
        "text_secondary": "#6b7280",
        "border": "#dce1e7",
        "hero_from": "#374151",
        "hero_to": "#6b7280",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#dc2626"
    },
    "cyber_green": {
        "accent": "#22c55e",
        "accent_2": "#4ade80",
        "accent_soft": "#102a1c",
        "accent_strong": "#86efac",
        "sidebar_bg": "#031b11",
        "sidebar_bg_2": "#010d08",
        "sidebar_text": "#f0fdf4",
        "sidebar_muted": "#bbf7d0",
        "workspace_bg": "#09120c",
        "card_bg": "#101c15",
        "card_bg_soft": "#14271d",
        "text_primary": "#f0fdf4",
        "text_secondary": "#bed8c5",
        "border": "#274734",
        "hero_from": "#031b11",
        "hero_to": "#15803d",
        "success": "#22c55e",
        "warning": "#fbbf24",
        "danger": "#fb7185"
    },
    "rose_gold": {
        "accent": "#d97786",
        "accent_2": "#f9a8d4",
        "accent_soft": "#fff1f2",
        "accent_strong": "#be5b6b",
        "sidebar_bg": "#7c2d4d",
        "sidebar_bg_2": "#4a1830",
        "sidebar_text": "#fff7fa",
        "sidebar_muted": "#fbcfe8",
        "workspace_bg": "#fff9fb",
        "card_bg": "#ffffff",
        "card_bg_soft": "#fff4f7",
        "text_primary": "#40202d",
        "text_secondary": "#7a5f69",
        "border": "#f2dbe2",
        "hero_from": "#7c2d4d",
        "hero_to": "#d97786",
        "success": "#16a34a",
        "warning": "#f59e0b",
        "danger": "#e11d48"
    },
    "aurora_purple": {
        "accent": "#7c3aed",
        "accent_2": "#22d3ee",
        "accent_soft": "#25124b",
        "accent_strong": "#c4b5fd",
        "sidebar_bg": "#1e1b4b",
        "sidebar_bg_2": "#120f2c",
        "sidebar_text": "#f5f3ff",
        "sidebar_muted": "#d8b4fe",
        "workspace_bg": "#110f20",
        "card_bg": "#1a1830",
        "card_bg_soft": "#231f3f",
        "text_primary": "#faf5ff",
        "text_secondary": "#d7ccf3",
        "border": "#3b3561",
        "hero_from": "#1e1b4b",
        "hero_to": "#7c3aed",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#fb7185"
    },
    "denim_light": {
        "accent": "#2563eb",
        "accent_2": "#93c5fd",
        "accent_soft": "#dbeafe",
        "accent_strong": "#1d4ed8",
        "sidebar_bg": "#1e3a8a",
        "sidebar_bg_2": "#172554",
        "sidebar_text": "#eff6ff",
        "sidebar_muted": "#bfdbfe",
        "workspace_bg": "#f5f9ff",
        "card_bg": "#ffffff",
        "card_bg_soft": "#f7fbff",
        "text_primary": "#16223c",
        "text_secondary": "#60718b",
        "border": "#dae4f5",
        "hero_from": "#1e3a8a",
        "hero_to": "#2563eb",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#ef4444"
    },
    "obsidian_red": {
        "accent": "#ef4444",
        "accent_2": "#f87171",
        "accent_soft": "#33181a",
        "accent_strong": "#fca5a5",
        "sidebar_bg": "#0f172a",
        "sidebar_bg_2": "#020617",
        "sidebar_text": "#f8fafc",
        "sidebar_muted": "#fecaca",
        "workspace_bg": "#0b1120",
        "card_bg": "#151b2c",
        "card_bg_soft": "#1d2638",
        "text_primary": "#f8fafc",
        "text_secondary": "#d6d8e1",
        "border": "#394052",
        "hero_from": "#0f172a",
        "hero_to": "#991b1b",
        "success": "#22c55e",
        "warning": "#fbbf24",
        "danger": "#ef4444"
    }
}

CSS_VARIABLE_KEYS: dict[str, str] = {
    "accent": "--accent",
    "accent_2": "--accent-2",
    "accent_soft": "--accent-soft",
    "accent_strong": "--accent-strong",
    "sidebar_bg": "--sidebar-bg",
    "sidebar_bg_2": "--sidebar-bg-2",
    "sidebar_text": "--sidebar-text",
    "sidebar_muted": "--sidebar-muted",
    "workspace_bg": "--workspace-bg",
    "card_bg": "--card-bg",
    "card_bg_soft": "--card-bg-soft",
    "text_primary": "--text-primary",
    "text_secondary": "--text-secondary",
    "border": "--border",
    "hero_from": "--hero-from",
    "hero_to": "--hero-to",
    "success": "--success",
    "warning": "--warning",
    "danger": "--danger",
}


def _theme_tokens(package_id: str, config: dict[str, Any] | None = None) -> dict[str, str]:
    clean_id = normalize_package_id(package_id)
    base = dict(THEME_TOKEN_OVERRIDES.get(clean_id, THEME_TOKEN_OVERRIDES[DEFAULT_APPEARANCE_PACKAGE]))
    custom = (config or {}).get("tokens") if isinstance(config, dict) else None
    if isinstance(custom, dict):
        for key, value in custom.items():
            if key in CSS_VARIABLE_KEYS and isinstance(value, str) and value.strip().startswith("#"):
                base[key] = value.strip()
    return base


def _css_variables(tokens: dict[str, str]) -> dict[str, str]:
    return {css_key: tokens[token_key] for token_key, css_key in CSS_VARIABLE_KEYS.items() if token_key in tokens}


def normalize_package_id(package_id: str) -> str:
    value = str(package_id or "").strip()
    return value if value in PACKAGE_MAP else DEFAULT_APPEARANCE_PACKAGE


def _decode_config(value: str | None) -> dict[str, Any]:
    try:
        data = json.loads(value or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def package_payload(package_id: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    clean_id = normalize_package_id(package_id)
    clean_config = dict(config or {})
    base = dict(PACKAGE_MAP[clean_id])
    tokens = _theme_tokens(clean_id, clean_config)
    css_vars = _css_variables(tokens)
    base.update({
        "accent": tokens["accent"],
        "accent_2": tokens["accent_2"],
        "accent_soft": tokens["accent_soft"],
        "accent_strong": tokens["accent_strong"],
        "sidebar": tokens["sidebar_bg"],
        "sidebar_bg": tokens["sidebar_bg"],
        "sidebar_bg_2": tokens["sidebar_bg_2"],
        "card_bg": tokens["card_bg"],
        "card_bg_soft": tokens["card_bg_soft"],
        "workspace_bg": tokens["workspace_bg"],
        "text_primary": tokens["text_primary"],
        "text_secondary": tokens["text_secondary"],
        "border": tokens["border"],
        "hero_from": tokens["hero_from"],
        "hero_to": tokens["hero_to"],
        "success": tokens["success"],
        "warning": tokens["warning"],
        "danger": tokens["danger"],
        "tokens": tokens,
        "css_variables": css_vars,
        "config": clean_config,
    })
    return base


def tenant_appearance_payload(tenant_id: str) -> dict[str, Any]:
    clean_tenant_id = str(tenant_id or DEFAULT_TENANT_ID).strip() or DEFAULT_TENANT_ID
    with get_conn() as conn:
        row = conn.execute(
            """SELECT id, name, appearance_package, appearance_config_json
               FROM tenants WHERE id=? AND COALESCE(deleted_at,'')=''""",
            (clean_tenant_id,),
        ).fetchone()
        if not row:
            row = conn.execute(
                """SELECT id, name, appearance_package, appearance_config_json
                   FROM tenants WHERE id=?""",
                (DEFAULT_TENANT_ID,),
            ).fetchone()
    if not row:
        return {"tenant_id": DEFAULT_TENANT_ID, "tenant_name": "Ana Kurum", "package": package_payload(DEFAULT_APPEARANCE_PACKAGE)}
    package_id = normalize_package_id(row["appearance_package"] if "appearance_package" in row.keys() else "")
    config = _decode_config(row["appearance_config_json"] if "appearance_config_json" in row.keys() else "{}")
    return {
        "tenant_id": row["id"],
        "tenant_name": row["name"],
        "package": package_payload(package_id, config),
    }


def appearance_for_user(username: str) -> dict[str, Any]:
    user = get_user(username, active_only=True)
    tenant_id = user_tenant_id(user) if user else DEFAULT_TENANT_ID
    return tenant_appearance_payload(tenant_id)


def appearance_catalog() -> list[dict[str, Any]]:
    return [dict(row) for row in APPEARANCE_PACKAGES]


def admin_appearance_payload(username: str) -> dict[str, Any]:
    user = get_user(username, active_only=True)
    if not is_super_admin_user(user):
        raise PermissionError("Görünüm paketlerini yalnızca Süper Admin yönetebilir.")
    tenants = list_tenants_admin(username, True)
    enriched = []
    for tenant in tenants:
        package_id = normalize_package_id(str(tenant.get("appearance_package", "") or ""))
        config = _decode_config(str(tenant.get("appearance_config_json", "{}") or "{}"))
        item = dict(tenant)
        item["appearance_package"] = package_id
        item["appearance_package_name"] = PACKAGE_MAP[package_id]["name"]
        item["appearance_config"] = config
        enriched.append(item)
    return {"packages": appearance_catalog(), "tenants": enriched, "default_package": DEFAULT_APPEARANCE_PACKAGE}


def update_tenant_appearance_admin(username: str, tenant_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    user = get_user(username, active_only=True)
    if not is_super_admin_user(user):
        raise PermissionError("Görünüm paketlerini yalnızca Süper Admin yönetebilir.")
    clean_tenant_id = str(tenant_id or "").strip()
    if not clean_tenant_id:
        raise ValueError("Kurum seçilmelidir.")
    package_id = normalize_package_id(str(payload.get("appearance_package", payload.get("package_id", "")) or ""))
    config = payload.get("appearance_config", payload.get("config", {}))
    if not isinstance(config, dict):
        config = {}
    with transaction() as conn:
        exists = conn.execute(
            "SELECT id FROM tenants WHERE id=? AND COALESCE(deleted_at,'')=''",
            (clean_tenant_id,),
        ).fetchone()
        if not exists:
            raise ValueError("Kurum bulunamadı veya arşivlenmiş.")
        conn.execute(
            """UPDATE tenants
               SET appearance_package=?, appearance_config_json=?, updated_at=?
               WHERE id=?""",
            (package_id, json.dumps(config, ensure_ascii=False), now_iso(), clean_tenant_id),
        )
    log_activity("Kurum görünüm paketi güncellendi", f"{clean_tenant_id}: {PACKAGE_MAP[package_id]['name']}", username, "")
    return tenant_appearance_payload(clean_tenant_id)
