# DENTIX Frontend Error Taxonomy & Resilient UI States

## 1. Frontend Error Taxonomy

| Error Category | HTTP Code | Frontend Handling Strategy | User Feedback (Arabic) |
|---|---|---|---|
| **Network / Offline** | `0 / NetworkError` | Display persistent offline banner; disable mutations; queue non-critical queries | "أنت غير متصل بالإنترنت حالياً. تم حفظ البيانات محلياً." |
| **Authentication Expired** | `401 Unauthorized` | Attempt silent token refresh via HTTP-only cookie; redirect to login if refresh fails | "انتهت الجلسة. يرجى تسجيل الدخول مرة أخرى." |
| **Permission Denied / RLS** | `403 Forbidden` | Render PermissionDeniedBoundary; block restricted action button | "ليس لديك الصلاحية الكافية لتنفيذ هذا الإجراء." |
| **Resource Gone** | `410 Gone` | Render DeprecatedSurfaceBoundary pointing to safe alternative | "هذه الخاصية لم تعد متاحة. يرجى استخدام أدوات التصدير الآمنة." |
| **Rate Limited** | `429 Too Many Requests` | Show toast with backoff timer countdown | "تم تجاوز الحد المسموح للطلبات. يرجى الانتظار قليلاً." |
| **Server Error** | `500 Internal Server Error` | Log sanitized trace ID; render ErrorFallback with Retry button | "حدث خطأ غير متوقع في الخادم. رمز الخطأ: {trace_id}" |

---

## 2. Server-State Query Cache Isolation
- `queryClient.clear()` is called unconditionally on user logout, session expiry, and tenant switching.
- Prevents cross-tenant state leakage between consecutive clinic sessions on shared clinic devices.
