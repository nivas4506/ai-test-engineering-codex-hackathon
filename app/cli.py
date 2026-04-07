#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="AI Test Engineering CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'run' command
    run_parser = subparsers.add_parser("run", help="Start the AI Test Engineering server")
    run_parser.add_argument("--host", default="127.0.0.1", help="Host IP address (default: 127.0.0.1)")
    run_parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    run_parser.add_argument("--dev", action="store_true", help="Run in development mode (with reload)")

    # 'init' command (maybe for setting up workspace)
    init_parser = subparsers.add_parser("init", help="Initialize the local workspace and environment")

    args = parser.parse_args()

    if args.command == "run":
        # Ensure workspace exists
        from app.core.config import WORKSPACE_ROOT, UPLOADS_DIR
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Start server
        print(f"🚀 Starting AI Test Engineering server at http://{args.host}:{args.port}")
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.dev)

    elif args.command == "init":
        print("🔧 Initializing workspace...")
        from app.db import init_database
        init_database()
        print("✅ Environment initialized successfully.")
        
    else:
        parser.print_help()
        sys.exit(0)

if __name__ == "__main__":
    main()
