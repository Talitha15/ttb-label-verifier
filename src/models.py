from dataclasses import dataclass, field


@dataclass
class OCRLine:
    """
    Represents one OCR-detected line and its approximate position.

    Coordinates are measured in image pixels. A value of 0 means Azure did
    not provide usable geometry for that line.
    """

    text: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2)


@dataclass
class OCRResult:
    """
    Stores the complete OCR text together with location-aware line data.
    """

    text: str = ""
    lines: list[OCRLine] = field(default_factory=list)


@dataclass
class LabelData:
    """
    Represents expected or detected alcohol label information.
    """

    beverage_type: str = ""
    brand_name: str = ""
    class_type: str = ""
    abv: str = ""
    net_contents: str = ""
    government_warning: str = ""


@dataclass
class FieldValidation:
    """
    Stores the validation result for one label field.
    """

    expected: str = ""
    detected: str = ""
    status: str = "Manual Review"
    message: str = ""


@dataclass
class ValidationResult:
    """
    Stores all field-level results and the overall validation status.
    """

    fields: dict[str, FieldValidation] = field(default_factory=dict)
    overall_status: str = "Manual Review"
