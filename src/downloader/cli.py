"""CLI: python -m src.downloader --subject "POO II" --raw-root ./data/raw"""

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

    parser = argparse.ArgumentParser(description="Descarga materiales del campus UNO")
    parser.add_argument("--subject", default=None,
                        help="Filtrar por materia. Acepta año al final: 'POO II 2026' o 'POO II 1C2026'")
    parser.add_argument("--raw-root", default="./data/raw",
                        help="Carpeta destino (default: ./data/raw)")
    parser.add_argument("--year", type=int, default=None,
                        help="Año del curso (default: año actual)")
    parser.add_argument("--headless", action="store_true",
                        help="Browser sin ventana")
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.set_defaults(headless=True)
    args = parser.parse_args()

    from src.downloader import download
    report = download(
        raw_root=Path(args.raw_root),
        subject_filter=args.subject,
        year=args.year,
        headless=args.headless,
    )

    print(f"\nDescargados: {len(report.files_downloaded)}")
    print(f"Existentes:  {len(report.files_skipped)}")
    print(f"Errores:     {len(report.errors)}")
    sys.exit(0 if not report.errors else 1)


if __name__ == "__main__":
    main()
