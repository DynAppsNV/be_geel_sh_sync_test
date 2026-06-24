# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from io import BytesIO
from reportlab.pdfgen import canvas

from odoo.exceptions import ValidationError
from odoo.tools.pdf import DependencyError, DictionaryObject, errors, NameObject, PdfFileReader, PdfFileWriter, PdfReadError
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)


def get_valid_pdf_data(pdf_bytes, strict=True):
    """
    Validate and return a readable PDF file object from the given byte data.

    :param pdf_bytes: Raw byte data of the PDF file to be validated.
    :param strict: Enforce strict parsing of the PDF file.
    :return: A valid and non-encrypted PdfFileReader instance.
    :raises ValidationError: If cannot return non-encrypted PdfFileReader instance.
    """
    # If strict=True is explicitly requested, try strict first then fall back to lenient.
    # By default we favor lenient parsing to cope with malformed yet readable PDFs.
    # pypdf strict=False enables best-effort parsing for PDFs that don't follow the spec exactly.
    # See https://pypdf.readthedocs.io/en/stable/user/robustness.html
    strict_modes = (True, False) if strict else (False,)
    for strict_flag in strict_modes:
        try:
            pdf_reader = PdfFileReader(BytesIO(pdf_bytes), strict_flag)
            if pdf_reader.isEncrypted:
                continue
            if strict_flag is False and strict:
                _logger.warning("Strict PDF parsing failed; falling back to lenient mode.")
            return pdf_reader
        except (DependencyError, UnicodeDecodeError, PdfReadError, errors.PyPdfError):
            _logger.warning("Failed to read PDF data (strict=%s).", strict_flag, exc_info=True)
            continue

    raise ValidationError(_lt(
        "It seems that we're not able to process one of the uploaded pdf. It is either"
        " encrypted, or encoded in a format we do not support."
    ))


def flatten_pdf(base64_pdf):
    """
    Flatten a PDF by rendering all form field values as static text and
    removing interactive form elements (/Annots and /AcroForm).

    :param base64_pdf: Base64-encoded string of the original PDF.
    :return: Base64-encoded string of the flattened, non-editable PDF.
    :raises ValidationError: If the PDF cannot be decoded or parsed.
    """
    try:
        pdf_bytes = base64.b64decode(base64_pdf)
        # Use lenient parsing to better handle malformed PDFs while still refusing encrypted ones.
        # strict=False allows pypdf to apply best-effort recovery for non-spec-compliant PDFs.
        pdf_reader = get_valid_pdf_data(pdf_bytes, strict=False)
        output_pdf = PdfFileWriter()
    except errors.PyPdfError as e:
        _logger.warning("Failed to parse PDF during flattening: %s", e)
        return base64_pdf

    try:
        form_fields = pdf_reader.getFormTextFields()
    except errors.PyPdfError as e:
        _logger.warning("Failed to read PDF form fields during flattening: %s", e)
        return base64_pdf

    if not form_fields:
        return base64_pdf

    try:
        page_count = pdf_reader.getNumPages()
    except errors.PyPdfError as e:
        _logger.warning("Failed to read PDF pages during flattening: %s", e)
        return base64_pdf

    for page_num in range(page_count):
        try:
            output_pdf.addPage(pdf_reader.getPage(page_num))
            page = output_pdf.getPage(-1)
            annotations = page.get("/Annots")
            if not annotations:
                continue

            # Dynamic page size
            page_width = float(page.mediaBox.getWidth())
            page_height = float(page.mediaBox.getHeight())
            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))

            # Draw each field value
            for annot_ref in annotations:
                _draw_field_value(can, annot_ref)

            # Save overlay and merge with original page
            can.save()
            packet.seek(0)  # reset cursor to beginning before reading

            # Read the overlay PDF we just created from memory
            # And place it on top of the original page to show the field values
            # Use strict=False for lenient parsing of the generated overlay PDF.
            overlay_pdf = PdfFileReader(packet, strict=False)
            # Skip merge if overlay has no pages (blank form with no values drawn).
            if overlay_pdf.getNumPages() > 0:
                page.mergePage(overlay_pdf.getPage(0))

            # Remove interactive annotations so the result is read-only
            del page["/Annots"]
            page.compressContentStreams()

        except errors.PyPdfError:
            return base64_pdf

    # Remove AcroForm metadata (fully disable interactive forms)
    output_pdf._root_object.update({
        NameObject("/AcroForm"): DictionaryObject()
    })

    output_stream = BytesIO()
    output_pdf.write(output_stream)
    return base64.b64encode(output_stream.getvalue())


def _draw_field_value(can, annot_ref):
    """
    Auxiliary function to draw a field value (text, checkbox, radio button).
    """
    annot = annot_ref.getObject()
    rect = annot.get("/Rect")
    if not rect:
        return
    field_value = _get_field_value(annot)
    if field_value:
        x, y = float(rect[0]), float(rect[1])
        can.setFont("Helvetica", 10)
        can.drawString(x + 2, y + 2, field_value)


def _get_field_value(annot):
    """ Return the display value extracted from a PDF annotation.

    :param annot: The annotation dictionary representing the PDF form field.
    :return: The string value to draw, or a checkmark character for active buttons.
    :rtype: str
    """
    field_type = annot.get("/FT")
    if field_type == "/Btn":  # checkbox or radio
        appearance_state = annot.get("/AS")
        if appearance_state and appearance_state != NameObject("/Off"):
            # Render a ✓ symbol for checked Check Box or Radio Button
            return chr(0x2713)
        else:  # if btn is not checked don't render anything
            return ""
    return str(annot.get("/V") or "")
