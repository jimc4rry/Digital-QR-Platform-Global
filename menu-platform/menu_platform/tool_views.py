import base64
from io import BytesIO

import qrcode
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.shortcuts import render
from django.utils.translation import gettext as _


def free_qr_code_generator(request):
    """Public, no-login QR code generator - an SEO lead magnet ("free qr code generator"
    has real search volume) with an upsell to the full product for anyone in hospitality
    who lands here. Stateless: nothing is saved server-side, the image is generated
    in-memory and returned as a data URI."""
    qr_image_data_uri = None
    submitted_url = ''
    error = None

    if request.method == 'POST':
        submitted_url = request.POST.get('url', '').strip()
        target_url = submitted_url
        if target_url and '://' not in target_url:
            target_url = f'https://{target_url}'

        if not target_url:
            error = _('Please enter a URL.')
        else:
            try:
                URLValidator()(target_url)
            except ValidationError:
                error = _("That doesn't look like a valid URL.")
            else:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(target_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color='black', back_color='white')

                buffer = BytesIO()
                img.save(buffer, 'PNG')
                encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
                qr_image_data_uri = f'data:image/png;base64,{encoded}'

    context = {
        'qr_image_data_uri': qr_image_data_uri,
        'submitted_url': submitted_url,
        'error': error,
    }
    return render(request, 'tools/free_qr_code_generator.html', context)
