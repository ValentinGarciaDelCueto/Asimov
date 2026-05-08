"""CLI: python -m src.organizer --raw ./data/raw --processed ./data/processed"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    parser = argparse.ArgumentParser(description="Organiza archivos descargados del campus")
    parser.add_argument("--raw", default="./data/raw", help="Carpeta raw (default: ./data/raw)")
    parser.add_argument("--processed", default="./data/processed",
                        help="Carpeta procesada (default: ./data/processed)")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra qué haría")
    args = parser.parse_args()

    from src.organizer import organize
    report = organize(
        raw_root=Path(args.raw),
        processed_root=Path(args.processed),
        dry_run=args.dry_run,
    )

    print(f"\nMovidos:    {len(report.moved)}")
    print(f"Renombrados: {len(report.renamed)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
