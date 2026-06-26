"""Carrot MCP CLI entry point."""

import sys
from importlib.metadata import entry_points


def get_servers():
    eps = entry_points(group="carrot_mcp.servers")
    return {ep.name: ep for ep in eps}


def main():
    servers = get_servers()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            print("Available servers:")
            for name in sorted(servers):
                print(f"  - {name}")
        elif cmd in servers:
            server = servers[cmd].load()
            server.run()
        else:
            print(f"Unknown server: {cmd}")
            print(f"Available: {', '.join(sorted(servers))}")
            sys.exit(1)
    else:
        print("Carrot MCP Server")
        print("Usage: carrot-mcp <server>")
        print(f"Available: {', '.join(sorted(servers))}")


if __name__ == "__main__":
    main()
