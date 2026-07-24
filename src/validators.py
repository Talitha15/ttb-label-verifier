import re
from dataclasses import dataclass

from src.models import FieldValidation, LabelData, ValidationResult


GOVERNMENT_WARNING_REQUIRED = """
GOVERNMENT WARNING:
(1) According to the Surgeon General, women should not drink alcoholic
beverages during pregnancy because of the risk of birth defects.
(2) Consumption of alcoholic beverages impairs your ability to drive a car
or operate machinery, and may cause health problems.
"""


@dataclass(frozen=True)
class NetContentsValue:
    amount: float
    unit: str


@dataclass(frozen=True)
class ABVValue:
    minimum: float
    maximum: float

    @property
    def is_range(self) -> bool:
        return self.minimum != self.maximum


def normalize_text(value: str) -> str:
    """
    Normalize text so differences in capitalization, punctuation,
    and extra spacing do not cause false mismatches.
    """

    normalized = value.casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def normalize_abv(value: str) -> str:
    """
    Extract and standardize the first ABV value.

    This helper remains for backward compatibility. Range-aware comparison
    is handled by parse_abv_value and validate_abv.
    """

    parsed = parse_abv_value(value)

    if parsed is None:
        return normalize_text(value)

    if parsed.is_range:
        return f"{parsed.minimum:g}-{parsed.maximum:g}"

    return f"{parsed.minimum:g}"


def parse_abv_value(value: str) -> ABVValue | None:
    """
    Parse an exact ABV or an ABV range.

    Supported examples:
        5.6
        5.6%
        4.5%-5%
        4.5 to 5
        between 4.5% and 5%
        not less than 4.5% and not more than 5%
    """

    normalized = value.casefold().replace("–", "-").replace("—", "-")

    bounded_patterns = (
        re.compile(
            r"not\s+less\s+than\s+"
            r"(\d{1,3}(?:\.\d+)?)\s*%?.*?"
            r"not\s+more\s+than\s+"
            r"(\d{1,3}(?:\.\d+)?)\s*%?"
        ),
        re.compile(
            r"not\s+more\s+than\s+"
            r"(\d{1,3}(?:\.\d+)?)\s*%?.*?"
            r"not\s+less\s+than\s+"
            r"(\d{1,3}(?:\.\d+)?)\s*%?"
        ),
        re.compile(
            r"between\s+(\d{1,3}(?:\.\d+)?)\s*%?\s*"
            r"(?:and|to|-)\s*"
            r"(\d{1,3}(?:\.\d+)?)\s*%?"
        ),
        re.compile(
            r"\b(\d{1,3}(?:\.\d+)?)\s*%?\s*"
            r"(?:to|through|-)\s*"
            r"(\d{1,3}(?:\.\d+)?)\s*%?"
        ),
    )

    for pattern in bounded_patterns:
        match = pattern.search(normalized)

        if not match:
            continue

        first = float(match.group(1))
        second = float(match.group(2))
        return ABVValue(
            minimum=min(first, second),
            maximum=max(first, second),
        )

    exact_match = re.search(
        r"\b(\d{1,3}(?:\.\d+)?)\s*%?",
        normalized,
    )

    if not exact_match:
        return None

    number = float(exact_match.group(1))
    return ABVValue(minimum=number, maximum=number)


def validate_abv(expected: str, detected: str) -> FieldValidation:
    """
    Compare exact and ranged ABV values.

    Exact-to-range or range-to-exact comparisons that overlap are routed to
    Manual Review because OCR may have captured only one boundary.
    """

    if not expected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="No expected ABV was provided.",
        )

    if not detected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="The alcohol-by-volume value was not detected by OCR.",
        )

    expected_value = parse_abv_value(expected)
    detected_value = parse_abv_value(detected)

    if expected_value is None or detected_value is None:
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message=(
                "The ABV value could not be interpreted reliably. "
                "A human reviewer must inspect the label."
            ),
        )

    tolerance = 0.01

    same_minimum = (
        abs(expected_value.minimum - detected_value.minimum)
        <= tolerance
    )
    same_maximum = (
        abs(expected_value.maximum - detected_value.maximum)
        <= tolerance
    )

    if same_minimum and same_maximum:
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Match",
            message="The detected ABV matches the expected value.",
        )

    ranges_overlap = not (
        detected_value.maximum < expected_value.minimum - tolerance
        or detected_value.minimum > expected_value.maximum + tolerance
    )

    if ranges_overlap and (
        expected_value.is_range != detected_value.is_range
    ):
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message=(
                "The detected ABV overlaps the expected range, but OCR may "
                "have captured only one range boundary. Verify the complete "
                "alcohol-content statement."
            ),
        )

    if ranges_overlap and (
        expected_value.is_range and detected_value.is_range
    ):
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message=(
                "The detected and expected ABV ranges overlap but are not "
                "identical. A human reviewer must verify the stated range."
            ),
        )

    return FieldValidation(
        expected=expected,
        detected=detected,
        status="Mismatch",
        message="The detected ABV does not match the expected value or range.",
    )


def _levenshtein_distance(first: str, second: str) -> int:
    """
    Return the minimum number of single-character edits needed to transform
    one string into the other.
    """

    if first == second:
        return 0

    if not first:
        return len(second)

    if not second:
        return len(first)

    previous_row = list(range(len(second) + 1))

    for first_index, first_character in enumerate(first, start=1):
        current_row = [first_index]

        for second_index, second_character in enumerate(second, start=1):
            insertion_cost = current_row[second_index - 1] + 1
            deletion_cost = previous_row[second_index] + 1
            substitution_cost = (
                previous_row[second_index - 1]
                + (first_character != second_character)
            )

            current_row.append(
                min(
                    insertion_cost,
                    deletion_cost,
                    substitution_cost,
                )
            )

        previous_row = current_row

    return previous_row[-1]


def _brand_words_have_likely_ocr_error(
    expected_words: list[str],
    detected_words: list[str],
) -> bool:
    """
    Identify a narrowly limited OCR-style typo in an otherwise matching brand.

    This is intentionally conservative:
    - The word counts must match.
    - All but one word must match exactly.
    - The one differing word must be at least four characters long.
    - That word may differ by only one character.
    """

    if len(expected_words) != len(detected_words):
        return False

    differing_pairs = [
        (expected_word, detected_word)
        for expected_word, detected_word in zip(
            expected_words,
            detected_words,
        )
        if expected_word != detected_word
    ]

    if len(differing_pairs) != 1:
        return False

    expected_word, detected_word = differing_pairs[0]

    if min(len(expected_word), len(detected_word)) < 4:
        return False

    return _levenshtein_distance(expected_word, detected_word) == 1


def parse_net_contents(value: str) -> NetContentsValue | None:
    """
    Parse a net-contents value into an amount and normalized unit.

    Unitless expected values are supported so an entry such as "341"
    can match OCR text such as "341 mL".
    """

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*"
        r"(ml|milliliters?|millilitres?|l|liters?|litres?|cl|"
        r"fl\.?\s*oz\.?|fluid ounces?)?\b",
        value.casefold(),
    )

    if not match:
        return None

    amount = float(match.group(1))
    raw_unit = (match.group(2) or "").replace(".", "")
    raw_unit = re.sub(r"\s+", " ", raw_unit).strip()

    unit_aliases = {
        "ml": "ml",
        "milliliter": "ml",
        "milliliters": "ml",
        "millilitre": "ml",
        "millilitres": "ml",
        "l": "l",
        "liter": "l",
        "liters": "l",
        "litre": "l",
        "litres": "l",
        "cl": "cl",
        "fl oz": "fl oz",
        "fluid ounce": "fl oz",
        "fluid ounces": "fl oz",
    }

    return NetContentsValue(
        amount=amount,
        unit=unit_aliases.get(raw_unit, raw_unit),
    )


def validate_standard_field(
    expected: str,
    detected: str,
    normalizer=normalize_text,
) -> FieldValidation:
    """
    Compare one expected value with one OCR-detected value.
    """

    if not expected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="No expected value was provided.",
        )

    if not detected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="The field was not detected by OCR.",
        )

    if normalizer(expected) == normalizer(detected):
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Match",
            message="The detected value matches the expected value.",
        )

    return FieldValidation(
        expected=expected,
        detected=detected,
        status="Mismatch",
        message="The detected value does not match the expected value.",
    )


def validate_brand_name(
    expected: str,
    detected: str,
) -> FieldValidation:
    """
    Validate brand names while preserving meaningful product modifiers.

    Exact normalized values are automatic matches. A strict whole-word
    containment relationship is routed to manual review rather than being
    accepted as a full match.
    """

    if not expected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="No expected brand name was provided.",
        )

    if not detected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="The brand name was not detected by OCR.",
        )

    normalized_expected = normalize_text(expected)
    normalized_detected = normalize_text(detected)

    if normalized_expected == normalized_detected:
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Match",
            message="The detected brand name matches the expected value.",
        )

    expected_words = normalized_expected.split()
    detected_words = normalized_detected.split()

    shorter = (
        expected_words
        if len(expected_words) <= len(detected_words)
        else detected_words
    )
    longer = (
        detected_words
        if len(expected_words) <= len(detected_words)
        else expected_words
    )

    is_contiguous_subset = any(
        longer[index:index + len(shorter)] == shorter
        for index in range(len(longer) - len(shorter) + 1)
    )

    if shorter and is_contiguous_subset:
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message=(
                "The brand values partially overlap, but one contains "
                "additional product wording that requires human review."
            ),
        )

    # Brand text frequently includes an otherwise-correct brand followed by
    # a product line, expression, reserve name, or beverage descriptor.
    # It may also contain one minor OCR or data-entry character difference,
    # such as KENDAL versus KENDALL. Compare same-length word windows so that
    # a likely brand phrase embedded in longer text is routed to human review
    # instead of being treated as a definite mismatch.
    if shorter:
        for index in range(len(longer) - len(shorter) + 1):
            candidate_window = longer[index:index + len(shorter)]

            word_distances = [
                _levenshtein_distance(left, right)
                for left, right in zip(shorter, candidate_window)
            ]

            allowable_distance = max(1, len(shorter))
            total_distance = sum(word_distances)
            changed_words = sum(
                distance > 0 for distance in word_distances
            )

            all_words_plausibly_related = all(
                distance <= 1
                or (
                    max(len(left), len(right)) >= 8
                    and distance <= 2
                )
                for left, right, distance in zip(
                    shorter,
                    candidate_window,
                    word_distances,
                )
            )

            if (
                all_words_plausibly_related
                and changed_words <= 1
                and total_distance <= allowable_distance
            ):
                return FieldValidation(
                    expected=expected,
                    detected=detected,
                    status="Manual Review",
                    message=(
                        "The detected text contains a likely version of the "
                        "expected brand plus additional product wording or "
                        "one minor OCR character difference. A human reviewer "
                        "must confirm the complete brand name."
                    ),
                )

    if _brand_words_have_likely_ocr_error(
        expected_words,
        detected_words,
    ):
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message=(
                "The brand names differ by one likely OCR character error. "
                "A human reviewer must confirm the stylized label text."
            ),
        )

    return FieldValidation(
        expected=expected,
        detected=detected,
        status="Mismatch",
        message="The detected brand name does not match the expected value.",
    )


def validate_class_type(
    expected: str,
    detected: str,
) -> FieldValidation:
    """
    Validate class/type values.

    Exact normalized wording is a match. A broader or shorter whole-word
    description is sent to manual review.
    """

    if not expected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="No expected class/type value was provided.",
        )

    if not detected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="The class/type value was not detected by OCR.",
        )

    normalized_expected = normalize_text(expected)
    normalized_detected = normalize_text(detected)

    if normalized_expected == normalized_detected:
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Match",
            message="The detected class/type matches the expected value.",
        )

    expected_words = normalized_expected.split()
    detected_words = normalized_detected.split()

    shorter = expected_words if len(expected_words) <= len(detected_words) else detected_words
    longer = detected_words if len(expected_words) <= len(detected_words) else expected_words

    is_contiguous_subset = any(
        longer[index:index + len(shorter)] == shorter
        for index in range(len(longer) - len(shorter) + 1)
    )

    if shorter and is_contiguous_subset:
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message=(
                "The values are related, but one is broader or more specific. "
                "A human reviewer must confirm the class/type."
            ),
        )

    return FieldValidation(
        expected=expected,
        detected=detected,
        status="Mismatch",
        message="The detected class/type does not match the expected value.",
    )


def validate_net_contents(
    expected: str,
    detected: str,
) -> FieldValidation:
    """
    Compare expected and OCR-detected net contents.

    A unitless expected value may match the same detected numeric amount
    with a unit. Conflicting explicit units remain mismatches.
    """

    if not expected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="No expected net-contents value was provided.",
        )

    if not detected.strip():
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Manual Review",
            message="The net contents were not detected by OCR.",
        )

    expected_value = parse_net_contents(expected)
    detected_value = parse_net_contents(detected)

    if expected_value is None or detected_value is None:
        return validate_standard_field(expected, detected)

    same_amount = abs(expected_value.amount - detected_value.amount) < 0.0001

    if not same_amount:
        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Mismatch",
            message="The detected net-contents amount does not match.",
        )

    if expected_value.unit and detected_value.unit:
        if expected_value.unit == detected_value.unit:
            return FieldValidation(
                expected=expected,
                detected=detected,
                status="Match",
                message="The detected net contents match the expected value.",
            )

        return FieldValidation(
            expected=expected,
            detected=detected,
            status="Mismatch",
            message=(
                "The numeric amount matches, but the stated units conflict."
            ),
        )

    return FieldValidation(
        expected=expected,
        detected=detected,
        status="Match",
        message=(
            "The numeric net-contents amount matches; the label also "
            "provides the unit of measure."
        ),
    )


GOVERNMENT_WARNING_PHRASES = (
    "according to the surgeon general",
    "women should not drink alcoholic beverages",
    "during pregnancy",
    "risk of birth defects",
    "consumption of alcoholic beverages",
    "impairs your ability to drive a car or operate machinery",
    "may cause health problems",
)


def _government_warning_phrase_coverage(
    detected_warning: str,
) -> tuple[int, int]:
    """
    Count required warning phrases without depending on sentence order.

    OCR may read small multi-line warning text out of sequence. Phrase-based
    coverage allows the validator to recognize that the wording is likely
    present while still requiring a human to verify order and formatting.
    """

    normalized = normalize_text(detected_warning)
    found = sum(
        normalize_text(phrase) in normalized
        for phrase in GOVERNMENT_WARNING_PHRASES
    )
    return found, len(GOVERNMENT_WARNING_PHRASES)


def validate_government_warning(detected: str) -> FieldValidation:
    """
    Evaluate government-warning wording using phrase coverage.

    This validator intentionally never returns Match. OCR cannot verify the
    required visual presentation, exact reading order, or bold heading, so a
    human reviewer must always make the final determination.
    """

    detected_warning = normalize_text(detected)

    if not detected_warning:
        return FieldValidation(
            expected=GOVERNMENT_WARNING_REQUIRED.strip(),
            detected=detected,
            status="Manual Review",
            message=(
                "The government warning was not detected. "
                "A human reviewer must inspect the label."
            ),
        )

    phrases_found, phrase_total = _government_warning_phrase_coverage(
        detected
    )

    if phrases_found >= phrase_total - 1:
        return FieldValidation(
            expected=GOVERNMENT_WARNING_REQUIRED.strip(),
            detected=detected,
            status="Manual Review",
            message=(
                f"{phrases_found} of {phrase_total} required warning "
                "phrases were detected. The wording appears substantially "
                "complete, but OCR reading order and required formatting "
                "must be visually confirmed."
            ),
        )

    if phrases_found >= 2:
        return FieldValidation(
            expected=GOVERNMENT_WARNING_REQUIRED.strip(),
            detected=detected,
            status="Manual Review",
            message=(
                f"{phrases_found} of {phrase_total} required warning "
                "phrases were detected. OCR could not verify the complete "
                "warning, so a human reviewer must inspect it."
            ),
        )

    return FieldValidation(
        expected=GOVERNMENT_WARNING_REQUIRED.strip(),
        detected=detected,
        status="Manual Review",
        message=(
            f"Only {phrases_found} of {phrase_total} required warning "
            "phrases were detected. A human reviewer must determine "
            "whether the required warning is present and complete."
        ),
    )


def determine_overall_status(
    field_results: dict[str, FieldValidation],
) -> str:
    """
    Determine the overall label status.

    Any mismatch makes the overall result a mismatch.
    Otherwise, any manual-review item requires manual review.
    """

    statuses = [result.status for result in field_results.values()]

    if "Mismatch" in statuses:
        return "Mismatch"

    if "Manual Review" in statuses:
        return "Manual Review"

    return "Match"


def validate_label(
    expected: LabelData,
    detected: LabelData,
) -> ValidationResult:
    """
    Compare expected label information with OCR-detected information.
    """

    field_results = {
        "beverage_type": validate_standard_field(
            expected.beverage_type,
            detected.beverage_type,
        ),
        "brand_name": validate_brand_name(
            expected.brand_name,
            detected.brand_name,
        ),
        "class_type": validate_class_type(
            expected.class_type,
            detected.class_type,
        ),
        "abv": validate_abv(
            expected.abv,
            detected.abv,
        ),
        "net_contents": validate_net_contents(
            expected.net_contents,
            detected.net_contents,
        ),
        "government_warning": validate_government_warning(
            detected.government_warning
        ),
    }

    return ValidationResult(
        fields=field_results,
        overall_status=determine_overall_status(field_results),
    )
