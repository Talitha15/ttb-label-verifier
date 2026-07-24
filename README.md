# AI-Powered Alcohol Label Verification App

**Take-Home Assessment for**  
**TTB IT Specialist (Artificial Intelligence)**

**Status:** ✅ Complete Prototype  
**Language:** Python  
**Framework:** Streamlit  
**OCR:** Azure AI Vision  
**Tests:** ✅ 46 Passing

---

# Project Overview

Hello! Thanks for checking out this project. I had a ton of fun and learned a lot. I developed this prototype web application as part of the TTB IT Specialist (Artificial Intelligence) take-home assessment.

The application assists label compliance reviewers by comparing expected application values against text extracted from an uploaded alcohol label image.

Azure AI Vision is used to perform Optical Character Recognition (OCR), while deterministic validation rules compare the extracted values to the expected application data. The application reports each field as **Match**, **Manual Review**, or **Mismatch**, allowing a human reviewer to make the final compliance determination.

The goal of this prototype is to demonstrate how AI can improve review efficiency while maintaining transparency and human oversight.

---

# Background

The Alcohol and Tobacco Tax and Trade Bureau (TTB) reviews approximately 150,000 alcohol label applications each year. Stakeholder interviews identified opportunities to reduce manual data entry and improve consistency by automatically extracting label information before comparing it with the submitted application.

Rather than replacing compliance specialists, this prototype is designed to assist reviewers by automating repetitive comparison tasks and highlighting fields that require additional attention.

---

# Solution Overview

The application follows a simple workflow:

1. The reviewer enters the expected application values.
2. An alcohol label image is uploaded.
3. Azure AI Vision extracts text from the label.
4. The application parses relevant fields.
5. Deterministic validation compares extracted values with the expected values.
6. Results are displayed as **Match**, **Manual Review**, or **Mismatch** for each field.

This approach keeps AI focused on text extraction while using transparent validation rules for compliance comparisons.

---

# Features

- Upload beer, wine, or distilled spirits label images
- OCR using Azure AI Vision
- Detection of:
  - Beverage Type
  - Brand Name
  - Class/Type
  - Alcohol by Volume (ABV)
  - Net Contents
  - Government Warning
- Deterministic field validation
- OCR tolerance for minor recognition errors
- Manual Review routing for ambiguous results
- Reset workflow for new verifications
- Automated test suite with **46 passing tests**

---

# Technology Stack

- Python
- Streamlit
- Azure AI Vision
- Pillow
- pytest
- python-dotenv

---

# System Architecture

The following diagram illustrates the high-level workflow of the application.

![System Architecture](docs/System-Architecture.png)

---

# Project Structure

```
app.py
src/
    extractor.py
    models.py
    parsers.py
    validators.py
tests/
requirements.txt
README.md
```

---

# Installation

Install the required packages:

```bash
pip install -r requirements.txt
```

Create a `.env` file containing your Azure AI Vision endpoint and API key.

Run the application:

```bash
streamlit run app.py
```

Run the automated tests:

```bash
pytest
```

---

# Example Workflow

1. Enter the expected application values.
2. Upload an alcohol label image.
3. Click **Analyze Label**.
4. Review the extracted values and validation results.
5. Use **Start New Verification** to begin another review.

---

# Design Decisions

When I planned this prototype, I wanted to keep the solution simple, transparent, and aligned with the stakeholder interviews.

Rather than asking AI to make compliance decisions, I used Azure AI Vision only for OCR. All comparisons are performed using deterministic validation rules that produce consistent and explainable results. Any uncertainty is routed to **Manual Review**, allowing a compliance specialist to make the final determination.

I believe this approach provides a good balance between automation and accountability while keeping the application easy to understand, test, and maintain.

---

# Assumptions

- Expected application values are available before verification begins.
- OCR quality depends on the clarity of the uploaded label image.
- Human reviewers make the final compliance decision.
- This application is intended as a standalone prototype and does not integrate with existing TTB systems.

---

# Known Limitations

- OCR accuracy depends on image quality.
- Decorative fonts and damaged labels may require manual review.
- The application validates a defined set of label fields and is not intended to replace a complete regulatory review.
- Batch processing and enterprise system integration are outside the scope of this prototype.

---

# Future Enhancements

Potential future improvements include:

- Integration with TTB application systems
- Batch processing of multiple labels
- Additional label field validation
- OCR confidence scoring
- Analytics and reporting
- Continuous improvement using reviewer feedback

---

# Lessons Learned

Building this project reinforced for me the importance of separating AI-assisted text extraction from business logic.

OCR can efficiently identify text on a label, but deterministic validation provides consistent and transparent comparisons against expected application data. Through testing across beer, wine, and distilled spirits labels, I found that routing uncertain cases to **Manual Review** produces more reliable behavior than trying to automate every edge case.

This experience also reinforced the value of designing AI solutions that assist people rather than replace them. For this proof of concept, keeping a human reviewer in the decision-making process felt like the most practical and responsible approach.

---

# Acknowledgements

This prototype was developed as part of the TTB IT Specialist (Artificial Intelligence) take-home assessment and is intended solely as a proof of concept demonstrating the practical use of AI-assisted document verification.