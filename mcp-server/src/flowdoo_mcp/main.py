import logging

from flowdoo_mcp.server import mcp
from flowdoo_mcp.tools import odoo


def main() -> None:
    # stdout carries the protocol; logging goes to stderr
    logging.basicConfig(level=logging.INFO)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
