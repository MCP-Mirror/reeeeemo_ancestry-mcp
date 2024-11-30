from .server import serve
"""
    Develop cmds for local run (Windows)
    pip uninstall mcp-server-ancestry
    pip install -e .
"""


def main():
    """MCP Ancestry Server - Takes GEDCOM files and provides functionality"""
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(
        description='give a model the ability to use GEDCOM files'
        )
    parser.add_argument(
        '--gedcom-path',
        type=str,
        required=True,
        help='Path to directory containing GEDCOM files'
        )
    
    args = parser.parse_args()
    
    asyncio.run(serve(args.gedcom_path))

if __name__ == "__main__":
    main()