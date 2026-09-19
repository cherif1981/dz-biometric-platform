"""Generate synthetic test images."""
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent


def make_card(path: Path) -> None:
    img = np.zeros((600, 900, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (850, 550), (240, 240, 240), -1)
    cv2.putText(img, "REPUBLIQUE ALGERIENNE", (80, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(img, "Nom: BENALI", (80, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "Prenom: Ahmed", (80, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "NIN: 123456789012345678", (80, 340),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "Ne le: 01/01/1990", (80, 400),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.imwrite(str(path), img)


def make_selfie(path: Path) -> None:
    img = np.full((400, 400, 3), 200, dtype=np.uint8)
    cv2.circle(img, (200, 180), 100, (150, 120, 100), -1)
    cv2.circle(img, (160, 150), 10, (0, 0, 0), -1)
    cv2.circle(img, (240, 150), 10, (0, 0, 0), -1)
    cv2.imwrite(str(path), img)


if __name__ == "__main__":
    make_card(HERE / "sample_card.jpg")
    make_selfie(HERE / "sample_selfie.jpg")
    print("Fixtures generated.")