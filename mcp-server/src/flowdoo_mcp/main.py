from pydantic import ValidationError
import sys
from flowdoo_mcp.config import get_settings


def main() -> None:

    try:
        get_settings() # check settings before start
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    # load all mpc tools
    import flowdoo_mcp.tools  # noqa: F401

    # start the mcp server
    from flowdoo_mcp.server import mcp

    mcp.run()


if __name__ == "__main__":
    main()