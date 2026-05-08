"""CLI: python -m src.processor --processed ./data/processed [--dry-run]"""

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

    parser = argparse.ArgumentParser(description="Resume PDFs y los sube a Drive")
    parser.add_argument("--processed", default="./data/processed",
                        help="Carpeta procesada (default: ./data/processed)")
    parser.add_argument("--subject", default=None, help="Filtrar por materia")
    parser.add_argument("--drive-folder", default=None,
                        help="ID de carpeta en Drive (opcional, auto-crea 'Resumenes UNO')")
    parser.add_argument("--dry-run", action="store_true", help="Sin API calls ni Drive")
    parser.add_argument("--reset", action="store_true", help="Reprocesar todos los archivos")
    args = parser.parse_args()

    from src.processor import process
    report = process(
        processed_root=Path(args.processed),
        drive_parent_folder_id=args.drive_folder,
        subject_filter=args.subject,
        dry_run=args.dry_run,
        reset=args.reset,
    )

    print(f"\nResumidos:  {len(report.summarized)}")
    print(f"Drive docs: {len(report.uploaded)}")
    print(f"Fallidos:   {len(report.failed)}")
    sys.exit(0 if not report.failed else 1)


if __name__ == "__main__":
    main()
