import os

from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

from src.models import OCRLine, OCRResult


load_dotenv()


def _get_polygon_points(line) -> list:
    """
    Return Azure polygon points while tolerating SDK naming differences.
    """

    polygon = getattr(line, "bounding_polygon", None)

    if polygon is None:
        polygon = getattr(line, "bounding_box", None)

    return list(polygon or [])


def _point_coordinate(point, axis: str) -> float:
    """
    Read x/y from either an SDK point object or a dictionary-like value.
    """

    value = getattr(point, axis, None)

    if value is None and isinstance(point, dict):
        value = point.get(axis)

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _line_geometry(line) -> tuple[float, float, float, float]:
    """
    Convert an Azure line polygon into x, y, width, and height.
    """

    points = _get_polygon_points(line)

    if not points:
        return 0.0, 0.0, 0.0, 0.0

    x_values = [_point_coordinate(point, "x") for point in points]
    y_values = [_point_coordinate(point, "y") for point in points]

    if not x_values or not y_values:
        return 0.0, 0.0, 0.0, 0.0

    x_min = min(x_values)
    x_max = max(x_values)
    y_min = min(y_values)
    y_max = max(y_values)

    return (
        x_min,
        y_min,
        max(0.0, x_max - x_min),
        max(0.0, y_max - y_min),
    )


def extract_text_from_image(image_bytes: bytes) -> OCRResult:
    """
    Send image bytes to Azure AI Vision and return text plus line locations.

    Args:
        image_bytes: The uploaded image represented as raw bytes.

    Returns:
        OCRResult containing the combined OCR text and one OCRLine per
        detected line.

    Raises:
        ValueError: If Azure credentials are missing.
        RuntimeError: If Azure does not return readable text.
    """

    endpoint = os.getenv("AZURE_VISION_ENDPOINT")
    key = os.getenv("AZURE_VISION_KEY")

    if not endpoint or not key:
        raise ValueError(
            "Azure Vision credentials are missing. "
            "Check the AZURE_VISION_ENDPOINT and AZURE_VISION_KEY values in .env."
        )

    client = ImageAnalysisClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    )

    result = client.analyze(
        image_data=image_bytes,
        visual_features=[VisualFeatures.READ],
    )

    if result.read is None or not result.read.blocks:
        raise RuntimeError("Azure OCR did not detect any readable text in the image.")

    detected_lines: list[OCRLine] = []

    for block in result.read.blocks:
        for line in block.lines:
            text = (line.text or "").strip()

            if not text:
                continue

            x, y, width, height = _line_geometry(line)

            detected_lines.append(
                OCRLine(
                    text=text,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                )
            )

    if not detected_lines:
        raise RuntimeError("Azure OCR did not detect any readable text in the image.")

    return OCRResult(
        text="\n".join(line.text for line in detected_lines),
        lines=detected_lines,
    )
