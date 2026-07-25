import re

from src.models import LabelData, OCRLine, OCRResult


BEVERAGE_TYPES = {
    "light beer": "Beer",
    "beer": "Beer",
    "ale": "Beer",
    "lager": "Beer",
    "pilsner": "Beer",
    "stout": "Beer",
    "porter": "Beer",
    "wine": "Wine",
    "cabernet sauvignon": "Wine",
    "chardonnay": "Wine",
    "merlot": "Wine",
    "pinot noir": "Wine",
    "sauvignon blanc": "Wine",
    "riesling": "Wine",
    "distilled spirits": "Distilled Spirits",
    "whiskey": "Distilled Spirits",
    "whisky": "Distilled Spirits",
    "bourbon": "Distilled Spirits",
    "vodka": "Distilled Spirits",
    "rum": "Distilled Spirits",
    "gin": "Distilled Spirits",
    "tequila": "Distilled Spirits",
}

CLASS_TYPE_KEYWORDS = [
    "cabernet sauvignon",
    "sauvignon blanc",
    "pinot noir",
    "pinot grigio",
    "chardonnay",
    "merlot",
    "riesling",
    "red wine",
    "white wine",
    "sparkling wine",
    "rosé wine",
    "rose wine",
    "bourbon whiskey",
    "straight bourbon",
    "rye whiskey",
    "blended whiskey",
    "whiskey",
    "whisky",
    "vodka",
    "rum",
    "gin",
    "tequila",
    "light beer",
    "ice beer",
    "wheat beer",
    "india pale ale",
    "double ipa",
    "pale ale",
    "amber ale",
    "brown ale",
    "cream ale",
    "hefeweizen",
    "doppelbock",
    "pilsner",
    "kölsch",
    "kolsch",
    "lager",
    "ale",
    "stout",
    "porter",
    "bock",
    "ipa",
]

BRAND_EXCLUSIONS = (
    "government warning",
    "surgeon general",
    "pregnancy",
    "birth defects",
    "health problems",
    "alcohol",
    "alc.",
    "alc ",
    "by volume",
    "net contents",
    "fluid ounce",
    "fl oz",
    "imported",
    "brewed",
    "bottled",
    "distributed",
    "adolph coors company",
    "company",
    "corporation",
    "inc.",
    "llc",
    "golden, colorado",
    "toronto",
    "barrie",
    "winnipeg",
    "regina",
    "edmonton",
    "est.",
    "established",
    "vintage",
    "napa valley",
    "smoothness and character",
    "smoothness",
    "character",
)

ADDRESS_OR_LEGAL_PATTERN = re.compile(
    r"\b(?:company|corporation|inc\.?|llc|ltd\.?|street|road|avenue|"
    r"boulevard|highway|colorado|california|new york|canada|u\.?s\.?a\.?)\b",
    re.IGNORECASE,
)


def _normalize_for_search(value: str) -> str:
    return " ".join(
        re.sub(r"[^a-z0-9]+", " ", value.casefold()).split()
    )


def _looks_like_measurement(line: str) -> bool:
    return bool(
        re.search(
            r"\b\d+(?:\.\d+)?\s*(?:%|ml|l|cl|fl\.?\s*oz\.?|fluid ounces?)\b",
            line,
            re.IGNORECASE,
        )
    )


def _looks_like_brand_line(line: str) -> bool:
    normalized = _normalize_for_search(line)

    if not normalized or len(normalized) < 2:
        return False

    if any(excluded in line.casefold() for excluded in BRAND_EXCLUSIONS):
        return False

    if ADDRESS_OR_LEGAL_PATTERN.search(line):
        return False

    if _looks_like_measurement(line):
        return False

    if "," in line or ";" in line:
        return False

    if line.rstrip().endswith((".", "!", "?")):
        return False

    words = normalized.split()

    prose_words = {
        "and",
        "with",
        "for",
        "from",
        "our",
        "the",
        "this",
        "that",
        "crafted",
        "brewed",
        "smoothness",
        "character",
        "quality",
        "taste",
        "flavor",
    }

    if len(words) >= 3 and sum(word in prose_words for word in words) >= 2:
        return False

    if len(words) > 5:
        return False

    return sum(character.isalpha() for character in line) >= 2


def _geometry_available(lines: list[OCRLine]) -> bool:
    return any(line.width > 0 and line.height > 0 for line in lines)


def _brand_line_score(
    line: OCRLine,
    index: int,
    max_height: float,
    image_center_x: float,
    use_geometry: bool,
) -> float:
    text = line.text
    normalized = _normalize_for_search(text)
    words = normalized.split()
    score = 0.0

    # Text-based signals remain available for tests and OCR results without
    # geometry.
    score += max(0, 8 - index) * 1.25

    if 1 <= len(words) <= 3:
        score += 6
    elif len(words) == 4:
        score += 3

    if 4 <= len(text) <= 28:
        score += 5
    elif len(text) <= 40:
        score += 2

    letters = [character for character in text if character.isalpha()]
    if letters:
        uppercase_ratio = (
            sum(character.isupper() for character in letters) / len(letters)
        )
        if uppercase_ratio >= 0.75:
            score += 3

    if text.istitle():
        score += 2

    if any(
        word in words
        for word in ("light", "lite", "reserve", "original", "gold", "black")
    ):
        score += 2

    if use_geometry and line.height > 0:
        # Prominent display text is usually larger than legal or side-panel
        # wording. Height carries the strongest location-aware signal.
        relative_height = line.height / max(max_height, 1.0)
        score += relative_height * 18

        # Favor text nearer the horizontal center while keeping the penalty
        # modest enough for intentionally off-center label designs.
        if image_center_x > 0:
            center_distance = abs(line.center_x - image_center_x)
            center_ratio = center_distance / image_center_x
            score += max(0.0, 1.0 - center_ratio) * 5

    return score


def _lines_form_display_pair(first: OCRLine, second: OCRLine) -> bool:
    """
    Determine whether two lines appear to be stacked brand display text.
    """

    if not (
        first.width > 0
        and first.height > 0
        and second.width > 0
        and second.height > 0
    ):
        return False

    horizontal_overlap = max(
        0.0,
        min(first.x + first.width, second.x + second.width)
        - max(first.x, second.x),
    )
    overlap_ratio = horizontal_overlap / max(
        1.0,
        min(first.width, second.width),
    )

    center_difference = abs(first.center_x - second.center_x)
    allowed_center_difference = max(
        first.width,
        second.width,
    ) * 0.45

    vertical_gap = second.y - (first.y + first.height)
    allowed_gap = max(first.height, second.height) * 2.5

    height_ratio = min(first.height, second.height) / max(
        first.height,
        second.height,
    )

    return (
        second.center_y > first.center_y
        and vertical_gap <= allowed_gap
        and vertical_gap >= -max(first.height, second.height)
        and (overlap_ratio >= 0.20 or center_difference <= allowed_center_difference)
        and height_ratio >= 0.35
    )


def _can_join_text(first: str, second: str) -> bool:
    first_words = _normalize_for_search(first).split()
    second_words = _normalize_for_search(second).split()
    combined_words = first_words + second_words

    return (
        len(combined_words) <= 5
        and len(first_words) <= 3
        and len(second_words) <= 3
        and not first.rstrip().endswith((".", "!", "?"))
        and not second.rstrip().endswith((".", "!", "?"))
    )


def _select_brand_name(
    lines: list[OCRLine],
    used_indexes: set[int],
) -> str:
    candidate_indexes = [
        index
        for index, line in enumerate(lines)
        if index not in used_indexes
        and _looks_like_brand_line(line.text)
    ]

    if not candidate_indexes:
        return ""

    use_geometry = _geometry_available(lines)
    max_height = max((line.height for line in lines), default=0.0)
    max_right = max((line.x + line.width for line in lines), default=0.0)
    image_center_x = max_right / 2 if max_right > 0 else 0.0

    # When OCR geometry is available, prioritize text located near the
    # horizontal center of the label. Side-panel text is usually descriptive
    # or regulatory wording rather than the primary brand.
    if use_geometry and image_center_x > 0:
        centered_indexes = []

        for index in candidate_indexes:
            line_center_distance = abs(
                lines[index].center_x - image_center_x
            )
            center_ratio = line_center_distance / image_center_x

            if center_ratio <= 0.35:
                centered_indexes.append(index)

        # Only apply the restriction when centered candidates actually exist.
        # This preserves support for labels whose brand is intentionally offset.
        if centered_indexes:
            candidate_indexes = centered_indexes
        
    candidates = [
        (
            index,
            lines[index],
                _brand_line_score(
                line=lines[index],
                index=index,
                max_height=max_height,
                image_center_x=image_center_x,
                use_geometry=use_geometry,
                ),
        )
        for index in candidate_indexes
    ]

    candidates.sort(key=lambda item: (-item[2], item[0]))
    best_index, best_line, best_score = candidates[0]

    # Evaluate every plausible pair instead of only pairing with the
    # highest-scoring single line. This allows a dominant centered pair such
    # as BUD + LIGHT to beat a large side-panel word such as GENUINE.
    pair_options: list[tuple[float, OCRLine, OCRLine]] = []

    for first_position, (
        first_index,
        first_candidate,
        first_score,
    ) in enumerate(candidates):
        for (
            second_index,
            second_candidate,
            second_score,
        ) in candidates[first_position + 1:]:
           
            first_text = first_candidate.text.strip()
            second_text = second_candidate.text.strip()

            # Do not join a prominent brand with a multiword lowercase
            # descriptive or marketing phrase.
            first_is_lower_phrase = (
                first_text.islower()
                and len(first_text.split()) >= 2
            )
            second_is_lower_phrase = (
                second_text.islower()
                and len(second_text.split()) >= 2
            )

            if (
                first_text.isupper()
                and second_is_lower_phrase
            ) or (
                second_text.isupper()
                and first_is_lower_phrase
            ):
                continue

            if use_geometry:
                if first_candidate.center_y <= second_candidate.center_y:
                    first, second = first_candidate, second_candidate
                else:
                    first, second = second_candidate, first_candidate

                if not _lines_form_display_pair(first, second):
                    continue

                pair_center_x = (
                    first.center_x + second.center_x
                ) / 2
                center_distance = abs(
                    pair_center_x - image_center_x
                )
                center_ratio = (
                    center_distance / image_center_x
                    if image_center_x > 0 else 0.0
                )

                average_height = (
                    first.height + second.height
                ) / 2
                relative_pair_height = (
                    average_height / max(max_height, 1.0)
                )

                width_balance = min(
                    first.width,
                    second.width,
                ) / max(first.width, second.width, 1.0)

                # A large, centered, vertically stacked pair should strongly
                # outrank isolated side-panel wording.
                pair_score = (
                    first_score
                    + second_score
                    + 18
                    + (relative_pair_height * 14)
                    + (max(0.0, 1.0 - center_ratio) * 12)
                    + (width_balance * 4)
                )

                pair_options.append(
                    (pair_score, first, second)
                )
            else:
                if abs(second_index - first_index) != 1:
                    continue

                if abs(first_score - second_score) > 5:
                    continue

                if first_index < second_index:
                    first, second = first_candidate, second_candidate
                else:
                    first, second = second_candidate, first_candidate

                pair_options.append(
                    (first_score + second_score, first, second)
                )

    if pair_options:
        pair_options.sort(key=lambda item: -item[0])
        pair_score, first, second = pair_options[0]

        # Require the pair to be meaningfully stronger than the best single
        # line so unrelated nearby words are not joined.
        if pair_score >= best_score + 8:
            return f"{first.text} {second.text}"

    return best_line.text


def _coerce_ocr_lines(
    ocr_input: str | OCRResult,
) -> tuple[str, list[OCRLine]]:
    if isinstance(ocr_input, OCRResult):
        text = ocr_input.text
        lines = [
            OCRLine(
                text=line.text.strip(),
                x=line.x,
                y=line.y,
                width=line.width,
                height=line.height,
            )
            for line in ocr_input.lines
            if line.text and line.text.strip()
        ]

        if lines:
            return text, lines

    text = str(ocr_input)
    lines = [
        OCRLine(text=line.strip())
        for line in text.splitlines()
        if line.strip()
    ]
    return text, lines


def parse_label_text(ocr_input: str | OCRResult) -> LabelData:
    """
    Convert OCR output into structured alcohol label fields.

    Plain strings remain supported for backward compatibility and unit tests.
    OCRResult enables location-aware brand scoring.
    """

    _, ocr_lines = _coerce_ocr_lines(ocr_input)
    lines = [line.text for line in ocr_lines]

    label = LabelData()
    used_indexes: set[int] = set()

    for index, line in enumerate(lines):
        normalized_line = line.casefold()

        for keyword, standardized_value in BEVERAGE_TYPES.items():
            if keyword in normalized_line:
                label.beverage_type = standardized_value
                used_indexes.add(index)
                break

        if label.beverage_type:
            break

    for index, line in enumerate(lines):
        normalized_line = line.casefold()

        for keyword in CLASS_TYPE_KEYWORDS:
            if keyword in normalized_line:
                label.class_type = line
                used_indexes.add(index)
                break

        if label.class_type:
            break

    abv_number_pattern = re.compile(
        r"\b(\d{1,3}(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    )
    abv_context_pattern = re.compile(
        r"\b(?:"
        r"abv"
        r"|alc(?:ohol)?\.?\s*[/\\-]?\s*"
        r"(?:by\s*)?vol(?:ume)?\.?"
        r")",
        re.IGNORECASE,
    )

    combined_text = " ".join(lines)

    range_patterns = (
        re.compile(
            r"not\s+less\s+than\s+"
            r"(\d{1,3}(?:\.\d+)?)\s*%.*?"
            r"not\s+more\s+than\s+"
            r"(\d{1,3}(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
        re.compile(
            r"not\s+more\s+than\s+"
            r"(\d{1,3}(?:\.\d+)?)\s*%.*?"
            r"not\s+less\s+than\s+"
            r"(\d{1,3}(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
        re.compile(
            r"between\s+(\d{1,3}(?:\.\d+)?)\s*%?\s*"
            r"(?:and|to|-)\s*"
            r"(\d{1,3}(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(\d{1,3}(?:\.\d+)?)\s*%\s*"
            r"(?:to|through|-)\s*"
            r"(\d{1,3}(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
    )

    for range_pattern in range_patterns:
        range_match = range_pattern.search(combined_text)

        if not range_match:
            continue

        first_value = float(range_match.group(1))
        second_value = float(range_match.group(2))
        minimum = min(first_value, second_value)
        maximum = max(first_value, second_value)

        label.abv = f"{minimum:g}%-{maximum:g}%"
        break

    if not label.abv:
        abv_candidates: list[tuple[float, int, str]] = []

        for index, line in enumerate(lines):
            for match in abv_number_pattern.finditer(line):
                value = float(match.group(1))
                score = 0.0

                same_line_context = bool(
                    abv_context_pattern.search(line)
                )
                nearby_text = " ".join(
                    lines[
                        max(0, index - 1):
                        min(len(lines), index + 2)
                    ]
                )
                nearby_context = bool(
                    abv_context_pattern.search(nearby_text)
                )

                if same_line_context:
                    score += 30
                elif nearby_context:
                    score += 18

                # Use alcohol wording as the strongest signal. Beer and
                # wine values are often below 30%, but distilled spirits
                # commonly exceed 30% (for example, 45% ALC./VOL.).
                if same_line_context:
                    if 0 < value <= 100:
                        score += 12
                    else:
                        score -= 30
                elif nearby_context:
                    if 0 < value <= 100:
                        score += 8
                    else:
                        score -= 30
                elif 0 < value <= 30:
                    score += 12
                else:
                    # A high percentage without alcohol context is probably
                    # marketing text such as "100% family owned."
                    score -= 30

                normalized_line = line.casefold()
                if any(
                    phrase in normalized_line
                    for phrase in (
                        "family owned",
                        "natural",
                        "recycled",
                        "organic",
                        "real juice",
                    )
                ):
                    score -= 20

                # Earlier lines win only when confidence is otherwise equal.
                score -= index * 0.01
                abv_candidates.append(
                    (score, index, f"{value:g}%")
                )

        if abv_candidates:
            abv_candidates.sort(
                key=lambda candidate: -candidate[0]
            )
            best_score, best_index, best_value = abv_candidates[0]

            # Require either alcohol context or a plausible beverage-strength
            # percentage. This preserves compatibility with labels that show
            # a plain "5.4%" without the context on the same OCR line.
            if best_score >= 10:
                label.abv = best_value
                used_indexes.add(best_index)

    net_contents_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*"
        r"(mL|milliliters?|millilitres?|"
        r"L|liters?|litres?|"
        r"cL|centiliters?|centilitres?|"
        r"fl\.?\s*oz\.?|fluid ounces?|ounces?)\b",
        re.IGNORECASE,
    )

    for index, line in enumerate(lines):
        match = net_contents_pattern.search(line)

        if match:
            amount = match.group(1)
            unit = match.group(2).casefold().replace(".", "").strip()

            if unit in {"ml", "milliliter", "milliliters", "millilitre", "millilitres"}:
                normalized_unit = "mL"
            elif unit in {"l", "liter", "liters", "litre", "litres"}:
                normalized_unit = "L"
            elif unit in {"cl", "centiliter", "centiliters", "centilitre", "centilitres"}:
                normalized_unit = "cL"
            elif unit.replace(" ", "") in {"floz", "fluidounce", "fluidounces"}:
                normalized_unit = match.group(2)   # Preserve original OCR formatting
            elif unit in {"ounce", "ounces"}:
                normalized_unit = match.group(2)
            else:
                normalized_unit = match.group(2)

            label.net_contents = f"{amount} {normalized_unit}"
            used_indexes.add(index)
            break

    warning_text = _extract_warning_block(ocr_lines)
    
    if warning_text:
        label.government_warning = warning_text
            
    label.brand_name = _select_brand_name(
        lines=ocr_lines,
        used_indexes=used_indexes,
    )

    return label

def _extract_warning_block(lines: list[OCRLine]) -> str:
    """
    Extract the government warning from the same visual side/column
    as the GOVERNMENT WARNING heading.

    This prevents OCR text from the opposite side of a bottle or can
    from being merged into the warning.
    """
    if not lines:
        return ""

    warning_index = next(
        (
            index
            for index, line in enumerate(lines)
            if "GOVERNMENT WARNING" in line.text.upper()
        ),
        None,
    )

    if warning_index is None:
        return ""

    warning_line = lines[warning_index]

    # Plain-text tests do not contain geometry.
    # Preserve the existing text-order behavior in that situation.
    if not _geometry_available(lines):
        return " ".join(
            line.text.strip()
            for line in lines[warning_index:]
            if line.text.strip()
        )

    image_right = max(
        (line.x + line.width for line in lines),
        default=0.0,
    )

    if image_right <= 0:
        return warning_line.text.strip()

    image_center_x = image_right / 2
    warning_center_x = warning_line.center_x

    warning_is_left = warning_center_x < image_center_x

    # Allow warning lines to extend toward the middle without crossing
    # deeply into the opposite side of the label.
    if warning_is_left:
        allowed_min_x = 0.0
        allowed_max_x = image_center_x * 1.10
    else:
        allowed_min_x = image_center_x * 0.90
        allowed_max_x = image_right

    warning_parts = [warning_line.text.strip()]
    previous_y = warning_line.y
    typical_height = max(warning_line.height, 1.0)

    stop_phrases = (
        "NUTRITION FACTS",
        "CALORIES",
        "PROTEIN",
        "INGREDIENTS",
        "BREWED BY",
        "BREWING COMPANY",
        "BOTTLED BY",
        "IMPORTED BY",
        "DISTRIBUTED BY",
        "REFUND",
        "DEPOSIT",
        "UPC",
    )

    for line in lines[warning_index + 1:]:
        text = line.text.strip()

        if not text:
            continue

        upper_text = text.upper()
        line_center_x = line.center_x

        # Ignore text from the opposite side, but keep searching.
        if not (allowed_min_x <= line_center_x <= allowed_max_x):
            continue

        # Ignore unrelated sections instead of ending the search.
        if any(phrase in upper_text for phrase in stop_phrases):
            continue
        
        vertical_gap = line.y - previous_y

        if vertical_gap > typical_height * 4.5:
            break

        warning_parts.append(text)
        previous_y = line.y
        typical_height = max(
            typical_height,
            line.height,
            1.0,
        )


    return " ".join(warning_parts)

   

