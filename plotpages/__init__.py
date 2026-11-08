"""Minimal helpers for building Dash multipage "dynamic plot" pages."""

from .errors import UserError, error_alert, error_figure
from .page import Param, configure, register_page_plot
from .theme import theme_provider

__all__ = ["Param", "UserError", "configure", "error_alert", "error_figure", "register_page_plot", "theme_provider"]
