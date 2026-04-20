import argparse
from .core import invert, correction

def main():
    parser = argparse.ArgumentParser(
        description="MeltInv command line interface"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # -------- correction command --------
    parser_corr = subparsers.add_parser(
        "correction",
        help="Run fractionation correction"
    )
    parser_corr.add_argument("file_name", type=str)
    parser_corr.add_argument("--src_Fo", type=float, default=0.9)
    parser_corr.add_argument("--max_olivine_addition", type=float, default=0.5)

    # -------- invert command --------
    parser_inv = subparsers.add_parser(
        "invert",
        help="Run inversion"
    )
    parser_inv.add_argument("file_name", type=str)
    parser_inv.add_argument("--depleted", nargs="+")
    parser_inv.add_argument("--correction", action="store_true")
    parser_inv.add_argument("--src_Fo", type=float, default=0.9)
    parser_inv.add_argument("--max_olivine_addition", type=float, default=0.5)
    parser_inv.add_argument("--make_figures", action="store_true")

    args = parser.parse_args()

    # -------- handle commands --------
    if args.command == "correction":
        correction(
            args.file_name,
            src_Fo=args.src_Fo,
            max_olivine_addition=args.max_olivine_addition
        )

    elif args.command == "invert":
        depleted_locations = tuple(args.depleted) if args.depleted else None

        invert(
            file_name=args.file_name,
            depleted_locations=depleted_locations,
            correction=args.correction,
            src_Fo=args.src_Fo,
            max_olivine_addition=args.max_olivine_addition,
            make_figures=args.make_figures
        )


if __name__ == "__main__":
    main()