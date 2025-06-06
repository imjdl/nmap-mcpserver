FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nmap \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src ./src/

# Install Python dependencies and the package
RUN pip install --no-cache-dir -e .

# Expose port if needed
# Note: MCP servers often use stdio, but if you need a port, uncomment and set accordingly
# EXPOSE 8080

# Run the MCP server
CMD ["python", "-m", "src.nmap_mcp"] 