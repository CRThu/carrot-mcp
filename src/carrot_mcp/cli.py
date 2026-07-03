"""Carrot MCP CLI entry point."""

import argparse
import shutil
import sys
from importlib.metadata import entry_points


def _get_servers():
    return {ep.name: ep for ep in entry_points(group="carrot_mcp.servers")}


def _get_agents():
    return {ep.name: ep.load() for ep in entry_points(group="carrot_mcp.agents")}


def _detect_local():
    return shutil.which("carrot-mcp") is not None


def _detect_uvx():
    return shutil.which("uvx") is not None


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
    if getattr(args, "uvx", False):
        use_uvx = True
    elif getattr(args, "local", False):
        use_uvx = False
    elif _detect_local():
        use_uvx = False
    elif _detect_uvx():
        use_uvx = True
    else:
        print("Error: neither 'carrot-mcp' nor 'uvx' found in PATH")
        sys.exit(1)
    mode = "uvx" if use_uvx else "local"
    targets = _filter_agents(agents, args.agents)
    for agent_name, agent in targets.items():
        if not agent.is_available():
            print(f"  {agent_name}: skipped (not installed)")
            continue
        existing = agent.list_carrot()
        local = agent.list_carrot_local()
        for name in list(local.keys()):
            agent.remove(name)
        count = 0
        for name in sorted(servers.keys()):
            agent.add(name, env=agent.get_env(existing.get(f"carrot-{name}", {})), use_uvx=use_uvx)
            count += 1
        remote_count = len(existing) - len(local)
        if remote_count:
            print(f"  {agent_name}: updated {count} server(s) ({mode}), skipped {remote_count} remote")
        else:
            print(f"  {agent_name}: updated {count} server(s) ({mode})")


def cmd_remove(args, servers, agents):
    targets = _filter_agents(agents, args.agents)
    for agent_name, agent in targets.items():
        if not agent.is_available():
            print(f"  {agent_name}: skipped (not installed)")
            continue
        count = 0
        for name in agent.list_carrot():
            agent.remove(name)
            count += 1
        print(f"  {agent_name}: removed {count} server(s)")


def _filter_agents(agents, names):
    if not names:
        return agents
    available = {n for n in agents}
    invalid = [n for n in names if n not in available]
    if invalid:
        print(f"Unknown agent(s): {', '.join(invalid)}")
        print(f"Available: {', '.join(sorted(available))}")
        sys.exit(1)
    return {n: agents[n] for n in names}


def main():
    parser = argparse.ArgumentParser(prog="carrot-mcp", description="Carrot MCP - A collection of MCP servers")
    sub = parser.add_subparsers(dest="command")

    sub_run = sub.add_parser("run", help="Run MCP server")
    sub_run.add_argument("server", help="Server name")

    sub_list = sub.add_parser("list", help="List available servers")

    sub_mcp = sub.add_parser("mcp", help="Manage MCP servers in agents")
    mcp_sub = sub_mcp.add_subparsers(dest="mcp_command")

    sub_add = mcp_sub.add_parser("add", help="Add all carrot servers to agents")
    sub_add.add_argument("agents", nargs="*", help="Agent name(s) (default: all)")
    sub_add.add_argument("--uvx", action="store_true", help="Use uvx command (auto-update)")
    sub_add.add_argument("--local", action="store_true", help="Use local carrot-mcp command")

    sub_remove = mcp_sub.add_parser("remove", help="Remove all carrot servers from agents")
    sub_remove.add_argument("agents", nargs="*", help="Agent name(s) (default: all)")

    args = parser.parse_args()

    if args.command is None:
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
    elif args.command == "mcp":
        if args.mcp_command is None:
            sub_mcp.print_help()
            return
        if args.mcp_command == "add":
            cmd_add(args, servers, _get_agents())
        elif args.mcp_command == "remove":
            cmd_remove(args, servers, _get_agents())


if __name__ == "__main__":
    main()
