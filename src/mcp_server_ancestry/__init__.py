from .server import serve
"""
    Wish to develop? pip instsall -e . in path\to\ancestry
"""


def main():
    """MCP Ancestry Server - Takes GEDCOM files and provides functionality"""
    import asyncio
    asyncio.run(serve())

if __name__ == "__main__":
    main()