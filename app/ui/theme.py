"""shadcn-inspired design tokens for CustomTkinter: colors, radii, spacing, fonts.

Colors are (light, dark) tuples usable directly as CTk fg_color/text_color/border_color —
CTk automatically picks the active element based on ctk.get_appearance_mode().
"""
from __future__ import annotations

import customtkinter as ctk

from app.config import APPEARANCE_DARK, APPEARANCE_LIGHT
from app.settings import update_settings

# ---- Colors ----
BACKGROUND = ("#f8f9fa", "#18181b")
SURFACE = ("#ffffff", "#232326")
SURFACE_MUTED = ("#f1f3f5", "#2a2a2e")
SURFACE_HOVER = ("#e9ecef", "#313135")
BORDER = ("#e2e4e8", "#3a3a40")

FOREGROUND = ("#18181b", "#f4f4f5")
MUTED_FOREGROUND = ("#6b7280", "#9ca3af")

PRIMARY = ("#2563eb", "#3b82f6")
PRIMARY_HOVER = ("#1d4ed8", "#2563eb")
PRIMARY_FOREGROUND = ("#ffffff", "#eff6ff")

DESTRUCTIVE = ("#dc2626", "#f87171")
DESTRUCTIVE_HOVER = ("#b91c1c", "#ef4444")
DESTRUCTIVE_FOREGROUND = ("#ffffff", "#1a0505")

SUCCESS = ("#16a34a", "#4ade80")
SUCCESS_HOVER = ("#15803d", "#22c55e")

WARNING = ("#d97706", "#fbbf24")

STATUS_COLORS = {
    "info": MUTED_FOREGROUND,
    "error": DESTRUCTIVE,
    "success": SUCCESS,
}

TYPE_BADGE_COLORS = {
    "string": ("#2563eb", "#3b82f6"),
    "hash": ("#7c3aed", "#a78bfa"),
    "list": ("#d97706", "#fbbf24"),
    "set": ("#0d9488", "#2dd4bf"),
    "zset": ("#dc2626", "#f87171"),
    "stream": ("#db2777", "#f472b6"),
}

# ---- Layout ----
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 20

FONT_FAMILY = "Segoe UI"
FONT_MONO_FAMILY = "Consolas"


def font_body(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def font_heading(size: int = 15) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight="bold")


def font_mono(size: int = 12) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_MONO_FAMILY, size=size)


def card_style() -> dict:
    return {
        "fg_color": SURFACE,
        "corner_radius": RADIUS_LG,
        "border_width": 1,
        "border_color": BORDER,
    }


def primary_button_style() -> dict:
    return {"fg_color": PRIMARY, "hover_color": PRIMARY_HOVER, "text_color": PRIMARY_FOREGROUND}


def destructive_button_style() -> dict:
    return {"fg_color": DESTRUCTIVE, "hover_color": DESTRUCTIVE_HOVER, "text_color": DESTRUCTIVE_FOREGROUND}


def success_button_style() -> dict:
    return {"fg_color": SUCCESS, "hover_color": SUCCESS_HOVER, "text_color": PRIMARY_FOREGROUND}


def ghost_button_style() -> dict:
    return {"fg_color": "transparent", "border_width": 1, "border_color": BORDER, "text_color": FOREGROUND}


def apply_appearance_mode(mode: str) -> None:
    """Sets CTk's active appearance mode and persists the choice."""
    mode = APPEARANCE_DARK if mode == APPEARANCE_DARK else APPEARANCE_LIGHT
    ctk.set_appearance_mode(mode)
    update_settings(appearance_mode=mode)
