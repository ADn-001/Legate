"""
Delivery-related routes (T3/Phase 4).

GET /delivery/template — returns the delivery email HTML template with
placeholder variables so the frontend can render a live preview client-side
(FR-30). The same template must be kept in sync with the one used by the
delivery worker; a single source of truth is maintained here.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.dependencies import get_current_verified_user

router = APIRouter()

# The delivery email template.
# Placeholders (filled client-side by the preview renderer):
#   {{CAPSULE_TITLE}}  — the capsule title (already HTML-escaped by the time
#                        the browser inserts it via textContent)
#   {{CAPSULE_BODY}}   — sanitized HTML body (rich text or escaped plain text)
#   {{MEDIA_HTML}}     — pre-rendered media section HTML (or empty string)
#   {{SENDER_NAME}}    — the nominator's name

DELIVERY_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A message for you from {{SENDER_NAME}}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f0f2f5; margin: 0; padding: 20px; color: #0d1117; }
  .container { max-width: 600px; margin: 0 auto; background: #ffffff;
               border-radius: 12px; overflow: hidden;
               box-shadow: 0 4px 24px rgba(0,0,0,0.10); }
  .header { background: linear-gradient(135deg, #3d4f6b, #2a3851);
            color: white; padding: 32px 40px; text-align: center; }
  .header h1 { margin: 0 0 8px; font-size: 24px; font-weight: 700; }
  .header p  { margin: 0; opacity: 0.85; font-size: 15px; }
  .body { padding: 32px 40px; }
  .capsule { border: 1px solid #e5e7eb; border-radius: 8px;
             padding: 24px; margin-bottom: 24px; }
  .capsule h3 { margin: 0 0 12px; font-size: 18px; color: #0d1117; }
  .capsule p  { margin: 0 0 10px; line-height: 1.6; color: #374151; }
  .capsule p:last-child { margin-bottom: 0; }
  .media { margin-top: 16px; }
  .media img { max-width: 100%; border-radius: 6px; margin-bottom: 8px; }
  .footer { background: #f9fafb; border-top: 1px solid #e5e7eb;
            padding: 20px 40px; text-align: center; }
  .footer p { margin: 0; font-size: 12px; color: #9ca3af; line-height: 1.5; }
  .disclaimer { background: #fffbeb; border: 1px solid #fcd34d;
                border-radius: 6px; padding: 12px 16px; margin-bottom: 24px; }
  .disclaimer p { margin: 0; font-size: 13px; color: #92400e; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>A message from {{SENDER_NAME}}</h1>
    <p>They wanted you to have this.</p>
  </div>
  <div class="body">
    <div class="disclaimer">
      <p><strong>Note:</strong> This is not a legal will or official document. It is a personal message delivered by Legate.</p>
    </div>
    <div class="capsule">
      <h3>{{CAPSULE_TITLE}}</h3>
      <div>{{CAPSULE_BODY}}</div>
      {{MEDIA_HTML}}
    </div>
  </div>
  <div class="footer">
    <p>Delivered by Legate &mdash; your digital legacy platform.<br>
       This message was prepared in advance and delivered automatically.</p>
  </div>
</div>
</body>
</html>"""


@router.get("/template", response_class=HTMLResponse)
async def get_delivery_template(
    _current_user=Depends(get_current_verified_user),
):
    """T3/FR-30: return the delivery email HTML template for client-side preview.
    The frontend fills in the placeholders using decrypted capsule content."""
    return HTMLResponse(content=DELIVERY_TEMPLATE)
