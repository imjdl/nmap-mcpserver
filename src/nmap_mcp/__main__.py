#!/usr/bin/env python3
"""
Main entry point for the nmap MCP server.
This allows running the server as `python -m src.nmap_mcp`.
"""

from . import main

if __name__ == "__main__":
    # Run the package's main function
    main() 