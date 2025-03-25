#!/usr/bin/env python3
"""
Simple test script for the nmap MCP server.
This script tests basic functionality without requiring a full MCP client.
"""

import asyncio
import sys
import time
from libnmap.process import NmapProcess
from libnmap.parser import NmapParser

async def test_nmap_functionality():
    """Test that we can run nmap scans and parse results."""
    print("Testing nmap functionality...")
    
    # Test local scan with minimal options to ensure nmap works
    target = "127.0.0.1"
    options = "-p 22,80 -sV"
    
    print(f"Running nmap scan on {target} with options: {options}")
    nm_process = NmapProcess(target, options)
    rc = nm_process.run()
    
    if rc != 0:
        print(f"Error running nmap: {nm_process.stderr}")
        return False
    
    try:
        parsed = NmapParser.parse(nm_process.stdout)
        
        print("\nScan results:")
        print(f"  Target: {target}")
        print(f"  Start time: {parsed.started}")
        print(f"  Hosts found: {len(parsed.hosts)}")
        
        for host in parsed.hosts:
            print(f"\n  Host: {host.address}")
            print(f"  Status: {host.status}")
            print(f"  Services:")
            
            for service in host.services:
                print(f"    - Port {service.port}/{service.protocol}: {service.state}")
                if service.service:
                    print(f"      Service: {service.service}")
                if service.banner:
                    print(f"      Banner: {service.banner}")
        
        print("\nNmap functionality test passed!")
        return True
        
    except Exception as e:
        print(f"Error parsing nmap results: {str(e)}")
        return False

if __name__ == "__main__":
    print("Nmap MCP Server Test Script")
    print("--------------------------")
    
    # Check if python-libnmap is installed
    try:
        print("Checking for python-libnmap...")
        import libnmap
        print(f"Found libnmap version: {libnmap.__version__}")
    except ImportError:
        print("Error: python-libnmap is not installed.")
        print("Please install it with: pip install python-libnmap")
        sys.exit(1)
    
    # Check if nmap is installed and available
    try:
        print("\nChecking for nmap...")
        test_process = NmapProcess("localhost", "-sV -p 22")
        test_process.run_background()
        
        # Wait for the process to complete with a timeout
        timeout = 30  # 30 seconds timeout
        start_time = time.time()
        while test_process.is_running() and time.time() - start_time < timeout:
            time.sleep(0.5)
            
        if test_process.is_running():
            test_process.stop()
            raise Exception("Nmap test timed out")
            
        if test_process.rc != 0:
            raise Exception(f"Nmap test failed with return code {test_process.rc}")
            
        print("Nmap is available and working.")
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Please make sure nmap is installed and available in your PATH.")
        sys.exit(1)
    
    # Run the async test
    print("\nRunning functional tests...")
    result = asyncio.run(test_nmap_functionality())
    
    if not result:
        print("\nTEST FAILED: There were errors during the test.")
        sys.exit(1)
    
    print("\nAll tests passed! The nmap MCP server should work correctly.")
    print("You can now run the server with: python -m src.nmap.server") 