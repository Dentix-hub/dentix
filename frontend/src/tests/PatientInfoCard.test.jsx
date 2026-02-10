/**
 * PatientInfoCard Component Tests
 * Verifies patient data display, action buttons, and null handling.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PatientInfoCard from '@/features/patients/PatientInfoCard';

// Mock dependencies
vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, opts) => {
            if (key === 'patientDetails.info_card.age_years') return `${opts?.age} years`;
            if (key === 'patientDetails.info_card.age_unknown') return 'Unknown age';
            if (key === 'patientDetails.info_card.no_phone') return 'No phone';
            if (key === 'patientDetails.info_card.basic_plan') return 'Basic';
            return key;
        },
    }),
}));

const mockPatient = {
    name: 'Ahmed Ali',
    age: 30,
    phone: '0501234567',
    address: '123 Main St, Cairo',
    default_price_list_id: null,
};

const mockHandlers = {
    onEdit: vi.fn(),
    onPrescription: vi.fn(),
    onNewAppointment: vi.fn(),
};

describe('PatientInfoCard', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders nothing when patient is null', () => {
        const { container } = render(
            <PatientInfoCard patient={null} {...mockHandlers} />
        );
        expect(container.innerHTML).toBe('');
    });

    it('displays patient name', () => {
        render(<PatientInfoCard patient={mockPatient} {...mockHandlers} />);
        expect(screen.getByText('Ahmed Ali')).toBeInTheDocument();
    });

    it('displays patient age', () => {
        render(<PatientInfoCard patient={mockPatient} {...mockHandlers} />);
        expect(screen.getByText('30 years')).toBeInTheDocument();
    });

    it('displays "Unknown age" when age is missing', () => {
        render(
            <PatientInfoCard patient={{ ...mockPatient, age: null }} {...mockHandlers} />
        );
        expect(screen.getByText('Unknown age')).toBeInTheDocument();
    });

    it('displays patient phone number', () => {
        render(<PatientInfoCard patient={mockPatient} {...mockHandlers} />);
        expect(screen.getByText('0501234567')).toBeInTheDocument();
    });

    it('displays "No phone" when phone is missing', () => {
        render(
            <PatientInfoCard patient={{ ...mockPatient, phone: null }} {...mockHandlers} />
        );
        expect(screen.getByText('No phone')).toBeInTheDocument();
    });

    it('displays patient address when provided', () => {
        render(<PatientInfoCard patient={mockPatient} {...mockHandlers} />);
        expect(screen.getByText('123 Main St, Cairo')).toBeInTheDocument();
    });

    it('hides address section when address is missing', () => {
        render(
            <PatientInfoCard patient={{ ...mockPatient, address: null }} {...mockHandlers} />
        );
        expect(screen.queryByText('123 Main St, Cairo')).not.toBeInTheDocument();
    });

    it('calls onEdit when edit button is clicked', () => {
        render(<PatientInfoCard patient={mockPatient} {...mockHandlers} />);
        fireEvent.click(screen.getByText('patientDetails.info_card.edit_data'));
        expect(mockHandlers.onEdit).toHaveBeenCalledTimes(1);
    });

    it('calls onPrescription when prescription button is clicked', () => {
        render(<PatientInfoCard patient={mockPatient} {...mockHandlers} />);
        fireEvent.click(screen.getByText('patientDetails.info_card.prescription'));
        expect(mockHandlers.onPrescription).toHaveBeenCalledTimes(1);
    });

    it('calls onNewAppointment when new appointment button is clicked', () => {
        render(<PatientInfoCard patient={mockPatient} {...mockHandlers} />);
        fireEvent.click(screen.getByText('patientDetails.info_card.new_appointment'));
        expect(mockHandlers.onNewAppointment).toHaveBeenCalledTimes(1);
    });

    it('shows "Basic" badge when no price list assigned', () => {
        render(<PatientInfoCard patient={mockPatient} {...mockHandlers} />);
        expect(screen.getByText('Basic')).toBeInTheDocument();
    });
});
