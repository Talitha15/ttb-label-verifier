import streamlit as st
from PIL import Image

from src.extractor import extract_text_from_image
from src.models import LabelData
from src.parsers import parse_label_text
from src.validators import validate_label


st.set_page_config(
    page_title="TTB Label Verifier",
    page_icon="🏷️",
    layout="wide",
)

if "verification_complete" not in st.session_state:
    st.session_state.verification_complete = False

if "form_version" not in st.session_state:
    st.session_state.form_version = 0

form_version = st.session_state.form_version

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1250px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        .app-subtitle, .section-description { color: #5f6368; }
        .app-subtitle {
            font-size: 1.05rem;
            margin-top: -0.5rem;
            margin-bottom: 2rem;
        }
        .section-description {
            margin-top: -0.5rem;
            margin-bottom: 1rem;
        }
        .status-banner {
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.25rem;
            font-size: 1.15rem;
            font-weight: 600;
        }
        .status-match {
            background-color: rgba(46, 160, 67, 0.12);
            border: 1px solid rgba(46, 160, 67, 0.35);
        }
        .status-review {
            background-color: rgba(245, 166, 35, 0.14);
            border: 1px solid rgba(245, 166, 35, 0.40);
        }
        .status-mismatch {
            background-color: rgba(220, 53, 69, 0.12);
            border: 1px solid rgba(220, 53, 69, 0.35);
        }
        .field-name {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .field-value-label {
            color: #5f6368;
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03rem;
        }
        .field-value {
            margin-top: 0.15rem;
            margin-bottom: 0.65rem;
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 10px;
            padding: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_missing_requirements(
    expected_label: LabelData,
    uploaded_file,
) -> dict[str, list[str]]:
    required_fields = {
        "Beverage Type": expected_label.beverage_type,
        "Brand Name": expected_label.brand_name,
        "Class / Type": expected_label.class_type,
        "Alcohol by Volume (ABV)": expected_label.abv,
        "Net Contents": expected_label.net_contents,
    }

    missing_requirements = {
        "Expected Label Information": [
            name for name, value in required_fields.items()
            if not value or not value.strip()
        ],
        "Label Image": [],
    }

    if uploaded_file is None:
        missing_requirements["Label Image"].append(
            "Upload a label image in PNG or JPEG format."
        )

    return {
        section: items
        for section, items in missing_requirements.items()
        if items
    }


def display_status_banner(overall_status: str) -> None:
    if overall_status == "Match":
        icon, title = "✅", "Label Information Matched"
        message = "All automatically evaluated fields matched the expected values."
        css_class = "status-match"
    elif overall_status == "Mismatch":
        icon, title = "❌", "Mismatch Detected"
        message = "One or more fields do not match the expected application values."
        css_class = "status-mismatch"
    else:
        icon, title = "⚠️", "Manual Review Required"
        message = "One or more fields could not be fully verified automatically."
        css_class = "status-review"

    st.markdown(
        f"""
        <div class="status-banner {css_class}">
            {icon} {title}
            <div style="font-size:0.92rem;font-weight:400;margin-top:0.3rem;">
                {message}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_status_icon(status: str) -> str:
    if status == "Match":
        return "✅"
    if status == "Mismatch":
        return "❌"
    return "⚠️"


def display_field_status(status: str) -> None:
    icon = get_status_icon(status)
    if status == "Match":
        st.success(f"{icon} Match")
    elif status == "Mismatch":
        st.error(f"{icon} Mismatch")
    else:
        st.warning(f"{icon} Manual Review")


def display_review_summary(
    match_count: int,
    review_count: int,
    mismatch_count: int,
) -> None:
    summary_items = [
        (
            "1 field matched automatically."
            if match_count == 1
            else f"{match_count} fields matched automatically."
        ),
        (
            "1 field requires manual verification."
            if review_count == 1
            else f"{review_count} fields require manual verification."
        ),
        (
            "No mismatched fields were detected."
            if mismatch_count == 0
            else (
                "1 mismatched field was detected."
                if mismatch_count == 1
                else f"{mismatch_count} mismatched fields were detected."
            )
        ),
    ]

    st.info(
        "**Review Summary**\n\n"
        + "\n\n".join(f"- {item}" for item in summary_items)
        + "\n\n**Final determination must be made by a human label reviewer.**"
    )


st.title("🏷️ AI-Powered Alcohol Label Verification")
st.markdown(
    """
    <div class="app-subtitle">
        Compare information detected on an alcohol beverage label against
        expected application values using Azure AI Vision OCR and
        deterministic validation rules.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("How this verification works"):
    st.markdown(
        """
        1. Enter the values expected to appear on the label.
        2. Upload a clear image of the alcohol beverage label.
        3. Select **Verify Label**.
        4. Review each field marked **Match**, **Mismatch**, or **Manual Review**.

        The system assists with label review but does not replace the final
        determination of a human reviewer.
        """
    )

input_column, image_column = st.columns([1, 1], gap="large")

with input_column:
    st.subheader("1. Expected Label Information")
    st.markdown(
        '<div class="section-description">'
        "Enter the information supplied in the label application."
        "</div>",
        unsafe_allow_html=True,
    )

    expected_label = LabelData(
        beverage_type=st.selectbox(
            "Beverage Type",
            ["", "Beer", "Wine", "Distilled Spirits"],
            key=f"beverage_type_{form_version}",
        ),
        brand_name=st.text_input(
            "Brand Name",
            placeholder="Example: Pine Ridge Vineyards",
            key=f"brand_name_{form_version}",
        ),
        class_type=st.text_input(
            "Class / Type",
            placeholder="Example: Cabernet Sauvignon",
            key=f"class_type_{form_version}",
        ),
        abv=st.text_input(
            "Alcohol by Volume (ABV)",
            placeholder="Example: 15.5",
            key=f"abv_{form_version}",
        ),
        net_contents=st.text_input(
            "Net Contents",
            placeholder="Example: 750 mL",
            key=f"net_contents_{form_version}",
        ),
    )

with image_column:
    st.subheader("2. Label Image")
    st.markdown(
        '<div class="section-description">'
        "Upload a PNG or JPEG image with readable label text."
        "</div>",
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Upload a label image",
        type=["png", "jpg", "jpeg"],
        key=f"uploaded_file_{form_version}",
    )

    if uploaded_file is not None:
        st.image(
            Image.open(uploaded_file),
            caption="Uploaded label image",
            use_container_width=True,
        )
    else:
        st.info("No label image has been uploaded yet.")

st.divider()

verify_clicked = st.button(
    "🔍 Verify Label",
    type="primary",
    use_container_width=True,
)

if verify_clicked:
    missing_requirements = get_missing_requirements(
        expected_label=expected_label,
        uploaded_file=uploaded_file,
    )

    if missing_requirements:
        st.warning("Please complete the following before starting verification.")
        for section_name, missing_items in missing_requirements.items():
            st.markdown(f"**{section_name}**")
            st.markdown("\n".join(f"- {item}" for item in missing_items))
    else:
        try:
            image_bytes = uploaded_file.getvalue()

            with st.spinner("Verifying label information...."):
                ocr_result = extract_text_from_image(image_bytes)
                detected_label = parse_label_text(ocr_result)

                validation_result = validate_label(
                    expected=expected_label,
                    detected=detected_label,
                )

                st.session_state.verification_complete = True

            st.divider()
            st.header("Verification Results")
            display_status_banner(validation_result.overall_status)

            field_results = list(validation_result.fields.values())
            match_count = sum(
                result.status == "Match" for result in field_results
            )
            mismatch_count = sum(
                result.status == "Mismatch" for result in field_results
            )
            review_count = sum(
                result.status not in {"Match", "Mismatch"}
                for result in field_results
            )
            total_fields = len(field_results)
            verified_percentage = (
                round((match_count / total_fields) * 100)
                if total_fields else 0
            )

            st.subheader("Results Summary")
            match_column, review_column, mismatch_column, score_column = (
                st.columns(4)
            )

            with match_column:
                st.metric(label="✅ Matches", value=match_count)
            with review_column:
                st.metric(label="⚠️ Manual Reviews", value=review_count)
            with mismatch_column:
                st.metric(label="❌ Mismatches", value=mismatch_count)
            with score_column:
                st.metric(
                    label="Automatically Verified",
                    value=f"{verified_percentage}%",
                )

            st.progress(
                verified_percentage / 100,
                text=(
                    f"{match_count} of {total_fields} fields "
                    "automatically verified"
                ),
            )

            display_review_summary(
                match_count=match_count,
                review_count=review_count,
                mismatch_count=mismatch_count,
            )

            st.subheader("Field-by-Field Review")

            field_labels = {
                "beverage_type": "Beverage Type",
                "brand_name": "Brand Name",
                "class_type": "Class / Type",
                "abv": "Alcohol by Volume",
                "net_contents": "Net Contents",
                "government_warning": "Government Warning",
            }

            for field_name, display_name in field_labels.items():
                field_result = validation_result.fields[field_name]
                status_icon = get_status_icon(field_result.status)

                with st.container(border=True):
                    title_column, status_column = st.columns([3, 1])

                    with title_column:
                        st.markdown(
                            f'<div class="field-name">'
                            f"{status_icon} {display_name}</div>",
                            unsafe_allow_html=True,
                        )

                    with status_column:
                        display_field_status(field_result.status)

                    expected_column, detected_column = st.columns(2)

                    with expected_column:
                        st.markdown(
                            '<div class="field-value-label">Expected</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="field-value">'
                            f'{field_result.expected or "Not provided"}'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    with detected_column:
                        st.markdown(
                            '<div class="field-value-label">Detected</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="field-value">'
                            f'{field_result.detected or "Not detected"}'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    st.caption(field_result.message)

            st.subheader("Analysis Details")
            detected_tab, ocr_tab = st.tabs(
                ["Detected Label Data", "Raw OCR Text"]
            )

            with detected_tab:
                detected_fields = {
                    "Beverage Type": detected_label.beverage_type,
                    "Brand Name": detected_label.brand_name,
                    "Class / Type": detected_label.class_type,
                    "ABV": detected_label.abv,
                    "Net Contents": detected_label.net_contents,
                    "Government Warning": detected_label.government_warning,
                }

                for label, value in detected_fields.items():
                    st.write(f"**{label}:**", value or "Not detected")

            with ocr_tab:
                st.text_area(
                    "OCR Results",
                    ocr_result.text,
                    height=300,
                    disabled=True,
                )

        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"Unable to analyze the label: {error}")

if st.session_state.verification_complete:
    st.divider()
    st.subheader("Next Step")
    st.write("Ready to review another label?")

    if st.button(
        "🆕 Start New Verification",
        use_container_width=True,
    ):
        next_form_version = st.session_state.form_version + 1

        for state_key in list(st.session_state.keys()):
            del st.session_state[state_key]

        st.session_state.form_version = next_form_version
        st.session_state.verification_complete = False
        st.rerun()