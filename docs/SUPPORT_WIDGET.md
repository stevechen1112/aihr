# Support Widget

UniHR now includes a built-in floating support widget in the main product UI.

## Exposed Actions

- Open product documentation
- Start an email to support
- Open a booking/support scheduling link

## Environment Variables

```env
SUPPORT_WIDGET_ENABLED=true
SUPPORT_EMAIL=support@yourdomain.com
SUPPORT_DOCS_URL=https://yourdomain.com/docs
SUPPORT_BOOKING_URL=https://cal.com/unihr/support
```

## API

- `GET /api/v1/public/support`

The frontend reads support settings from this public endpoint so the widget can work on both authenticated and unauthenticated branding contexts without hardcoding tenant-specific values into the bundle.