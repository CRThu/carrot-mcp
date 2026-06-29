"""Carrot MCP CLI entry point."""

import argparse
import sys
from importlib.metadata import entry_points


def _get_servers():
    return {ep.name: ep for ep in entry_points(group="carrot_mcp.servers")}


def _get_agents():
    return {ep.name: ep.load() for ep in entry_points(group="carrot_mcp.agents")}


def cmd_run(args, servers):
    if args.server not in servers:
        print(f"Unknown server: {args.server}")
        print(f"Available: {', '.join(sorted(servers))}")
        sys.exit(1)
    servers[args.server].load().run()


def cmd_list(args, servers):
    print("Available servers:")
    for name in sorted(servers):
        print(f"  - {name}")


def cmd_add(args, servers, agents):
    for agent_name, agent in agents.items():
        if not agent.is_available():
            print(f"  {agent_name}: skipped (not installed)")
            continue
        existing = agent.list_carrot()
        for name in list(existing.keys()):
            agent.remove(name)
        count = 0
        for name in sorted(servers.keys()):
            agent.add(name, env=agent.get_env(existing.get(name, {})))
            count += 1
        print(f"  {agent_name}: updated {count} server(s)")


def cmd_remove(args, servers, agents):
    for agent_name, agent in agents.items():
        if not agent.is_available():
            print(f"  {agent_name}: skipped (not installed)")
            continue
        count = 0
        for name in agent.list_carrot():
            agent.remove(name)
            count += 1
        print(f"  {agent_name}: removed {count} server(s)")


def main():
    parser = argparse.ArgumentParser(prog="carrot-mcp", description="Carrot MCP - A collection of MCP servers")
    sub = parser.add_subparsers(dest="command")

    sub_run = sub.add_parser("run", help="Run MCP server")
    sub_run.add_argument("server", help="Server name")

    sub_list = sub.add_parser("list", help="List available servers")

    sub_add = sub.add_parser("add", help="Add all carrot servers to all agents")

    sub_remove = sub.add_parser("remove", help="Remove all carrot servers from all agents")

    args = parser.parse_args()

    if not args.server if hasattr(args, "server") else args.command is None:
        parser.print_help()
        print()
        servers = _get_servers()
        print("Available servers:")
        for name in sorted(servers):
            print(f"  - {name}")
        return

    servers = _get_servers()

    if args.command == "run":
        cmd_run(args, servers)
    elif args.command == "list":
        cmd_list(args, servers)
    elif args.command == "add":
        cmd_add(args, servers, _get_agents())
    elif args.command == "remove":
        cmd_remove(args, servers, _get_agents())


if __name__ == "__main__":
    main()
