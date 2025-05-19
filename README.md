# Nmap MCP Server

[![smithery badge](https://smithery.ai/badge/@imjdl/nmap-mcpserver)](https://smithery.ai/server/@imjdl/nmap-mcpserver)

This is a Model Control Protocol (MCP) server that provides access to nmap network scanning functionality.

## Features

- Run nmap scans on specified targets with customizable options
- Store and retrieve scan results
- Analyze scan results using AI prompts

## Installation

### Installing via Smithery

To install Nmap MCP Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@imjdl/nmap-mcpserver):

```bash
npx -y @smithery/cli install @imjdl/nmap-mcpserver --client claude
```

### Installing Manually
Requirements:
- Python 3.10+
- python-libnmap
- nmap (installed on the system)

```bash
pip install python-libnmap
```

Make sure nmap is installed on your system:
```bash
# On Debian/Ubuntu
sudo apt-get install nmap

# On Fedora/CentOS
sudo dnf install nmap
```

## Usage

### Running the Server

To run the server directly from the source code:

```bash
python -m src.nmap_mcp
```

To install the package and run as a command:

```bash
pip install -e .
nmap-mcp
```

### Available Tools

1. **run-nmap-scan**
   - Run an nmap scan on specified targets
   - Parameters:
     - `target`: Target host or network (e.g., 192.168.1.1 or 192.168.1.0/24)
     - `options`: Nmap options (e.g., -sV -p 1-1000)

2. **get-scan-details**
   - Get detailed information about a specific scan
   - Parameters:
     - `scan_id`: ID of the scan to retrieve

3. **list-all-scans**
   - List all available scan results
   - No parameters required

### Available Prompts

1. **analyze-scan**
   - Analyze an nmap scan result
   - Parameters:
     - `scan_id`: ID of the scan to analyze
     - `focus`: Focus area (security/services/overview)

### Resources

Scan results are available as resources with the `nmap://scan/{scan_id}` URI scheme.

## Example Workflow

1. Run a scan:
   ```
   Call tool: run-nmap-scan
   Parameters: {"target": "192.168.1.0/24", "options": "-sV -p 22,80,443"}
   ```

2. Get scan details:
   ```
   Call tool: get-scan-details
   Parameters: {"scan_id": "<scan_id from previous step>"}
   ```

3. List all scans:
   ```
   Call tool: list-all-scans
   ```

4. Analyze scan results:
   ```
   Get prompt: analyze-scan
   Parameters: {"scan_id": "<scan_id>", "focus": "security"}
   ```

## Security Considerations

This server executes nmap commands on your system. Be cautious when scanning networks you don't own or have permission to scan, as unauthorized scanning may be illegal in some jurisdictions.

## Troubleshooting

If you encounter errors related to nmap not being found or being executed incorrectly:

1. Make sure nmap is installed and available in your PATH
2. Check the logs for which nmap executable is being used
3. The server will attempt to use the full path to nmap to avoid conflicts

## Docker Usage

You can run the MCP server in a Docker container:

```bash
# Build the Docker image
docker build -t nmap-mcp-server .

# Run the Docker container
docker run -it --rm nmap-mcp-server
```

For integration with the Glama MCP directory, the Docker container allows others to easily use this MCP server without worrying about installation dependencies.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
