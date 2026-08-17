export const DEFAULT_TENANT_TIMEZONE = 'Africa/Cairo';

/**
 * Return YYYY-MM-DD for an instant as seen in the clinic/tenant timezone.
 * Business-day grouping must not depend on the viewer browser timezone.
 */
export function getDateInTimeZone(timeZone = DEFAULT_TENANT_TIMEZONE, value = new Date()) {
    const instant = value instanceof Date ? value : new Date(value);
    const partsFor = (zone) => new Intl.DateTimeFormat('en-CA', {
        timeZone: zone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    }).formatToParts(instant);

    let parts;
    try {
        parts = partsFor(timeZone || DEFAULT_TENANT_TIMEZONE);
    } catch {
        parts = partsFor(DEFAULT_TENANT_TIMEZONE);
    }

    const values = Object.fromEntries(
        parts.filter((part) => part.type !== 'literal').map((part) => [part.type, part.value])
    );
    return `${values.year}-${values.month}-${values.day}`;
}

/**
 * Appointment.date_time is a clinic-local wall-clock string in the current
 * DENTIX schema. Compare its date prefix directly; never convert it to UTC.
 */
export function selectAppointmentsForBusinessDate(appointments, businessDate) {
    if (!businessDate || !Array.isArray(appointments)) return [];
    return appointments.filter((appointment) => appointment?.date_time?.startsWith(businessDate));
}
