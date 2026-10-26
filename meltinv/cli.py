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
    parser_inv.add_argument("--individual_sample_figures", "--make_figures", action="store_true")
    parser_inv.add_argument("--no_group_comparison_figure", dest="group_comparison_figure",
                            action="store_false")
    # Every sample is always inverted individually; --per_sample is accepted and ignored
    parser_inv.add_argument("--per_sample", action="store_true", help=argparse.SUPPRESS)

    parser_inv.add_argument("--plot_archive", help="Save diagnostics for later replotting")
    parser_plot = subparsers.add_parser("plot", help="Regenerate figures from a saved archive")
    parser_plot.add_argument("archive")
    parser_plot.add_argument("--output_dir", default="inversion_figures")
    parser_plot.add_argument("--no_individual", action="store_true")
    parser_plot.add_argument("--no_groups", action="store_true")

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
            individual_sample_figures=args.individual_sample_figures,
            group_comparison_figure=args.group_comparison_figure,
            plot_archive=args.plot_archive
        )

    elif args.command == "plot":
        from .plot_archive import regenerate_figures
        regenerate_figures(args.archive, args.output_dir,
                           individual_sample_figures=not args.no_individual,
                           group_comparison_figure=not args.no_groups)


if __name__ == "__main__":
    main()
