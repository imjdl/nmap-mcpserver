"""
Nmap MCP Server Package

This package provides an MCP (Model Control Protocol) interface for running nmap scans.
It allows AI assistants to run network scans and analyze the results.
"""

__version__ = "0.1.0"

from . import server
import asyncio

def main():
    """Main entry point for the package."""
    asyncio.run(server.main())

# Optionally expose other important items at package level
__all__ = ['main', 'server']