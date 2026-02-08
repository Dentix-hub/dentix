from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # 1. HSTS (Strict-Transport-Security)
        # Force HTTPS for 1 year (31536000 seconds) + includeSubDomains
        # Only meaningful if served over HTTPS, but good to set.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # 2. X-Content-Type-Options
        # Prevent MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 3. X-Frame-Options
        # Prevent Clickjacking (allow from same origin if needed, or DENY)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # 4. X-XSS-Protection
        # Legacy browser protection (mostly superseded by CSP, but good defense-in-depth)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 5. Content-Security-Policy (CSP)
        # Start strictly but allow necessary sources.
        # - default-src 'self': Only allow content from own domain.
        # - script-src: Allow self + unsafe-inline (often needed for React/inline JS) -- 
        #   Ideally we remove unsafe-inline later.
        # - style-src: Allow self + unsafe-inline (CSS-in-JS used by many libs).
        # - img-src: Allow self + data: (base64 images) + https: (external images).
        # - connect-src: Allow self + https: (API calls).
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; " 
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' https:;"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # 6. Referrer-Policy
        # Control how much referrer info is sent
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
