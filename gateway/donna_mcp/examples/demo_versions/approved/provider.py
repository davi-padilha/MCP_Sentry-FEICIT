"""Versao aprovada do provedor ativo da demonstracao."""

from donna_mcp.providers.simulated import SimulatedProvider


class ActiveDemoProvider(SimulatedProvider):
    """Provedor local aprovado, sem capacidades ocultas."""

    name = "simulated-approved-active"
