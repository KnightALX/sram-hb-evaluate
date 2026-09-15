"""gf_layout_flow: parametric BEOL / hybrid-bonding layout + RC geometry metrics."""

from __future__ import annotations

from gf_layout_flow.tech.pdk import activate_pdk

__version__ = "0.7.0"

activate_pdk()

__all__ = ["__version__", "activate_pdk"]
