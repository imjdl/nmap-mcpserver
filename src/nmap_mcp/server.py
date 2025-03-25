import asyncio
import json
import uuid
import time
import logging
import shutil
import subprocess
from typing import Dict, List, Optional, Set

from libnmap.process import NmapProcess
from libnmap.parser import NmapParser
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("nmap-mcp")

# Store scan results as a dictionary with scan_id as the key
scan_results: Dict[str, Dict] = {}

# Track ongoing scans to prevent duplicates
ongoing_scans: Set[str] = set()

# Rate limiting settings
RATE_LIMIT_PERIOD = 60  # seconds
RATE_LIMIT_MAX_SCANS = 3
last_scan_times = []

# Find the full path to the nmap executable
NMAP_PATH = shutil.which("nmap")
if not NMAP_PATH:
    logger.error("Could not find nmap executable. Please ensure nmap is installed.")
    # Default to standard path if not found
    NMAP_PATH = "/usr/bin/nmap"

logger.info(f"Using nmap executable at: {NMAP_PATH}")

server = Server("nmap")

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available scan results as resources.
    Each scan result is exposed as a resource with a custom nmap:// URI scheme.
    """
    return [
        types.Resource(
            uri=AnyUrl(f"nmap://scan/{scan_id}"),
            name=f"Scan: {scan_data.get('target', 'Unknown')}",
            description=f"Nmap scan of {scan_data.get('target', 'Unknown')} - {scan_data.get('timestamp', 'Unknown')}",
            mimeType="application/json",
        )
        for scan_id, scan_data in scan_results.items()
    ]

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read a specific scan result by its URI.
    The scan ID is extracted from the URI path component.
    """
    if uri.scheme != "nmap":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    scan_id = uri.path
    if scan_id is not None:
        scan_id = scan_id.lstrip("/")
        if scan_id in scan_results:
            return json.dumps(scan_results[scan_id], indent=2)
    raise ValueError(f"Scan result not found: {scan_id}")

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts related to nmap scanning.
    """
    return [
        types.Prompt(
            name="analyze-scan",
            description="Analyze an nmap scan result",
            arguments=[
                types.PromptArgument(
                    name="scan_id",
                    description="ID of the scan to analyze",
                    required=True,
                ),
                types.PromptArgument(
                    name="focus",
                    description="Focus area (security/services/overview)",
                    required=False,
                )
            ],
        )
    ]

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """
    Generate a prompt for analyzing nmap scan results.
    """
    if name != "analyze-scan":
        raise ValueError(f"Unknown prompt: {name}")

    if not arguments or "scan_id" not in arguments:
        raise ValueError("Missing scan_id argument")

    scan_id = arguments["scan_id"]
    focus = arguments.get("focus", "overview")

    if scan_id not in scan_results:
        raise ValueError(f"Scan result not found: {scan_id}")

    scan_data = scan_results[scan_id]
    
    focus_prompt = ""
    if focus == "security":
        focus_prompt = "Focus on security vulnerabilities and potential risks."
    elif focus == "services":
        focus_prompt = "Focus on identifying running services and their versions."
    else:  # overview
        focus_prompt = "Provide a general overview of the scan results."

    return types.GetPromptResult(
        description=f"Analyze nmap scan results for {scan_data.get('target', 'Unknown')}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Analyze the following nmap scan results. {focus_prompt}\n\n{json.dumps(scan_data, indent=2)}",
                ),
            )
        ],
    )

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools for nmap scanning.
    """
    return [
        types.Tool(
            name="run-nmap-scan",
            description="Run an nmap scan on specified targets",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target host or network (e.g., 192.168.1.1 or 192.168.1.0/24)"},
                    "options": {"type": "string", "description": "Nmap options (e.g., -sV -p 1-1000)"},
                },
                "required": ["target"],
            },
        ),
        types.Tool(
            name="get-scan-details",
            description="Get detailed information about a specific scan",
            inputSchema={
                "type": "object",
                "properties": {
                    "scan_id": {"type": "string", "description": "ID of the scan to retrieve"},
                },
                "required": ["scan_id"],
            },
        ),
        types.Tool(
            name="list-all-scans",
            description="List all available scan results",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        )
    ]

def check_rate_limit() -> bool:
    """Check if we're exceeding the rate limit."""
    global last_scan_times
    current_time = time.time()
    
    # Remove timestamps older than the rate limit period
    last_scan_times = [t for t in last_scan_times if current_time - t < RATE_LIMIT_PERIOD]
    
    # Check if we're under the limit
    return len(last_scan_times) < RATE_LIMIT_MAX_SCANS

def add_scan_timestamp():
    """Add current timestamp to track rate limiting."""
    global last_scan_times
    last_scan_times.append(time.time())

def run_nmap_directly(target, options):
    """Run nmap directly using subprocess instead of relying on python-libnmap."""
    try:
        # Construct the basic command with XML output
        cmd = [NMAP_PATH, "-oX", "-"]
        
        # Split options into separate arguments
        if options:
            option_args = options.split()
            cmd.extend(option_args)
            
        # Add target at the end
        cmd.append(target)
        logger.info(f"Executing nmap command: {' '.join(cmd)}")
        
        # Run the command and capture both stdout and stderr
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=False,
            check=True
        )
        
        return process.stdout, None
    except subprocess.CalledProcessError as e:
        return None, f"nmap failed with exit code {e.returncode}: {e.stderr.decode('utf-8', errors='replace')}"
    except Exception as e:
        return None, str(e)

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests for nmap scanning.
    """
    if not arguments and name != "list-all-scans":
        raise ValueError("Missing arguments")

    if name == "run-nmap-scan":
        target = arguments.get("target")
        options = arguments.get("options", "-sV")  # Default to version detection

        if not target:
            raise ValueError("Missing target")
            
        # Create a unique scan identifier based on target and options
        scan_key = f"{target}:{options}"
        
        # Check if an identical scan is already running
        if scan_key in ongoing_scans:
            return [
                types.TextContent(
                    type="text",
                    text=f"A scan with the same target and options is already running. Please wait for it to complete.",
                )
            ]
            
        # Check rate limiting
        if not check_rate_limit():
            return [
                types.TextContent(
                    type="text",
                    text=f"Rate limit exceeded. Please wait before starting another scan. Maximum {RATE_LIMIT_MAX_SCANS} scans per {RATE_LIMIT_PERIOD} seconds.",
                )
            ]
            
        try:
            # Mark this scan as ongoing
            ongoing_scans.add(scan_key)
            add_scan_timestamp()
            
            logger.info(f"Starting nmap scan on {target} with options {options}")
            
            # Use direct subprocess call instead of NmapProcess
            stdout, stderr = run_nmap_directly(target, options)
            
            if stderr:
                logger.error(f"Nmap scan failed: {stderr}")
                return [
                    types.TextContent(
                        type="text",
                        text=f"Nmap scan failed: {stderr}",
                    )
                ]

            # Parse results - convert bytes to string first
            try:
                xml_string = stdout.decode('utf-8', errors='replace')
                parsed = NmapParser.parse_fromstring(xml_string)
            except Exception as e:
                logger.error(f"Error parsing nmap results: {str(e)}")
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error parsing nmap results: {str(e)}",
                    )
                ]
            
            # Generate a unique ID for this scan
            scan_id = str(uuid.uuid4())
            
            # Store scan results
            scan_results[scan_id] = {
                "target": target,
                "options": options,
                "timestamp": parsed.started,
                "hosts": [
                    {
                        "address": host.address,
                        "status": host.status,
                        "hostnames": [
                            hostname.name if hasattr(hostname, 'name') else str(hostname)
                            for hostname in host.hostnames
                        ],
                        "services": [
                            {
                                "port": service.port,
                                "protocol": service.protocol,
                                "state": service.state,
                                "service": service.service,
                                "banner": service.banner
                            }
                            for service in host.services
                        ]
                    }
                    for host in parsed.hosts
                ]
            }
            
            # Notify clients that new resources are available
            await server.request_context.session.send_resource_list_changed()
            
            logger.info(f"Scan completed. Found {len(parsed.hosts)} hosts. Scan ID: {scan_id}")
            
            return [
                types.TextContent(
                    type="text",
                    text=f"Scan completed. Found {len(parsed.hosts)} hosts. Scan ID: {scan_id}",
                )
            ]
        except Exception as e:
            logger.error(f"Error during nmap scan: {str(e)}")
            return [
                types.TextContent(
                    type="text",
                    text=f"Error during nmap scan: {str(e)}",
                )
            ]
        finally:
            # Remove from ongoing scans when done
            ongoing_scans.discard(scan_key)
            
    elif name == "get-scan-details":
        scan_id = arguments.get("scan_id")
        
        if not scan_id:
            raise ValueError("Missing scan_id")
            
        if scan_id not in scan_results:
            return [
                types.TextContent(
                    type="text",
                    text=f"Scan with ID {scan_id} not found",
                )
            ]
            
        scan_data = scan_results[scan_id]
        
        # Extract summary information
        hosts_up = sum(1 for host in scan_data.get("hosts", []) if host.get("status") == "up")
        total_ports = sum(len(host.get("services", [])) for host in scan_data.get("hosts", []))
        
        return [
            types.TextContent(
                type="text",
                text=f"Scan of {scan_data.get('target')} (ID: {scan_id}):\n"
                     f"- Options: {scan_data.get('options')}\n"
                     f"- Timestamp: {scan_data.get('timestamp')}\n"
                     f"- Hosts: {len(scan_data.get('hosts', []))} ({hosts_up} up)\n"
                     f"- Total ports/services: {total_ports}\n\n"
                     f"Use the nmap://scan/{scan_id} resource to access full results",
            )
        ]
    elif name == "list-all-scans":
        if not scan_results:
            return [
                types.TextContent(
                    type="text",
                    text="No scans have been performed yet.",
                )
            ]
            
        scan_list = []
        for scan_id, scan_data in scan_results.items():
            hosts_count = len(scan_data.get("hosts", []))
            scan_list.append(f"- Scan ID: {scan_id}")
            scan_list.append(f"  Target: {scan_data.get('target')}")
            scan_list.append(f"  Options: {scan_data.get('options')}")
            scan_list.append(f"  Hosts: {hosts_count}")
            scan_list.append("")
            
        return [
            types.TextContent(
                type="text",
                text="Available scans:\n\n" + "\n".join(scan_list),
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    logger.info("Starting nmap MCP server")
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="nmap",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )