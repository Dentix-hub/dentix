import React, { useMemo } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import listPlugin from '@fullcalendar/list';
import { useTranslation } from 'react-i18next';
import './WeeklyCalendar.css';

const WeeklyCalendar = ({ appointments, onEventClick, onEventDrop, onSelectSlot }) => {
    const { t, i18n } = useTranslation();
    const isRtl = i18n.language === 'ar';

    const events = useMemo(() => {
        return appointments.map(appt => ({
            id: appt.id.toString(),
            title: appt.patient_name || t('appointments.table.patient'),
            start: appt.date_time,
            end: new Date(new Date(appt.date_time).getTime() + (appt.duration_minutes || 30) * 60000).toISOString(),
            extendedProps: { ...appt },
            className: `appt-status-${appt.status.toLowerCase().replace(' ', '-')}`
        }));
    }, [appointments, t]);

    return (
        <div className="weekly-calendar-container animate-in fade-in duration-500">
            <FullCalendar
                plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]}
                initialView="dayGridMonth"
                headerToolbar={{
                    left: isRtl ? 'timeGridWeek,dayGridMonth,listWeek' : 'prev,next today',
                    center: 'title',
                    right: isRtl ? 'prev,next today' : 'dayGridMonth,timeGridWeek,listWeek'
                }}
                direction={isRtl ? 'rtl' : 'ltr'}
                locale={i18n.language}
                events={events}
                editable={true}
                selectable={true}
                selectMirror={true}
                dayMaxEvents={true}
                weekends={true}
                nowIndicator={true}
                slotMinTime="08:00:00"
                slotMaxTime="23:00:00"
                allDaySlot={false}
                eventClick={(info) => onEventClick && onEventClick(info.event.extendedProps)}
                eventDrop={(info) => {
                    const { event } = info;
                    onEventDrop && onEventDrop(event.id, event.startStr);
                }}
                select={(info) => onSelectSlot && onSelectSlot(info.startStr)}
                height="700px"
                eventTimeFormat={{
                    hour: 'numeric',
                    minute: '2-digit',
                    meridiem: 'short'
                }}
                slotLabelFormat={{
                    hour: 'numeric',
                    minute: '2-digit',
                    omitZeroMinute: false,
                    meridiem: 'short'
                }}
            />
        </div>
    );
};

export default React.memo(WeeklyCalendar);
