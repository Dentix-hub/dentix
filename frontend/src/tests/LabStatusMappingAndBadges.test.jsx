import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { mapLabOrderStatus } from '@/features/clinical-chart/domain';
import ClinicalChartInspector from '@/features/clinical-chart/components/ClinicalChartInspector';
import DentalChartSVG from '@/features/dental/DentalChartSVG';

describe('Slice S29: Lab Status Mapping, Work-Item Badge Notification & Duplicate-Billing Regression', () => {
    describe('G12-M10: Lab Status Mapping (Decision D4)', () => {
        it('maps completed status variations to lab_ready', () => {
            expect(mapLabOrderStatus('completed')).toBe('lab_ready');
            expect(mapLabOrderStatus('COMPLETED')).toBe('lab_ready');
            expect(mapLabOrderStatus(' Completed ')).toBe('lab_ready');
        });

        it('maps all other statuses to unmapped neutral state', () => {
            expect(mapLabOrderStatus('pending')).toBe('unmapped');
            expect(mapLabOrderStatus('in_progress')).toBe('unmapped');
            expect(mapLabOrderStatus('delivered')).toBe('unmapped');
            expect(mapLabOrderStatus('cancelled')).toBe('unmapped');
            expect(mapLabOrderStatus('custom_status')).toBe('unmapped');
            expect(mapLabOrderStatus(null)).toBe('unmapped');
            expect(mapLabOrderStatus(undefined)).toBe('unmapped');
            expect(mapLabOrderStatus('')).toBe('unmapped');
        });
    });

    describe('G12-M11 & G12-M12: ClinicalChartInspector Lab Badges & Metadata', () => {
        const mockCopy = {
            labReady: 'Lab Ready',
            shade: 'Shade',
            material: 'Material',
            inLab: 'In Lab',
            sendToLab: 'Send to Lab',
        };

        it('renders lab-ready badge when work item has isLabReady: true', () => {
            const mockToothState = {
                findings: [],
                procedures: [
                    {
                        id: 101,
                        code: 'PROS_CROWN',
                        name: 'Crown Restoration',
                        status: 'active',
                        isLabReady: true,
                        shade: 'A2',
                        material: 'Zirconia',
                    },
                ],
            };

            render(
                <ClinicalChartInspector
                    copy={mockCopy}
                    selection={{ toothKey: '21' }}
                    toothState={mockToothState}
                    patientId={42}
                />
            );

            const badge = screen.getByTestId('lab-status-badge-101');
            expect(badge).toBeInTheDocument();
            expect(badge).toHaveTextContent(/Lab Ready/i);

            // Verify shade and material metadata
            const metadata = screen.getByTestId('item-shade-material-101');
            expect(metadata).toHaveTextContent('Zirconia');
            expect(metadata).toHaveTextContent(/Shade: A2/i);
        });

        it('renders lab-ready badge when linked lab order has status: completed', () => {
            const mockToothState = {
                findings: [],
                procedures: [
                    {
                        id: 102,
                        code: 'PROS_CROWN',
                        name: 'Crown Restoration',
                        status: 'active',
                    },
                ],
            };

            const mockLabOrders = [
                {
                    id: 55,
                    work_item_id: 102,
                    tooth_number: '21',
                    status: 'completed',
                    shade: '3M2',
                    material: 'E-Max',
                },
            ];

            render(
                <ClinicalChartInspector
                    copy={mockCopy}
                    selection={{ toothKey: '21' }}
                    toothState={mockToothState}
                    labOrders={mockLabOrders}
                    patientId={42}
                />
            );

            const badge = screen.getByTestId('lab-status-badge-102');
            expect(badge).toBeInTheDocument();
            expect(badge).toHaveTextContent(/Lab Ready/i);

            const metadata = screen.getByTestId('item-shade-material-102');
            expect(metadata).toHaveTextContent('E-Max');
            expect(metadata).toHaveTextContent(/Shade: 3M2/i);
        });

        it('does not render lab-ready badge when lab order is pending or in_progress', () => {
            const mockToothState = {
                findings: [],
                procedures: [
                    {
                        id: 103,
                        code: 'PROS_CROWN',
                        name: 'Crown Restoration',
                        status: 'active',
                        isLabReady: false,
                    },
                ],
            };

            const mockLabOrders = [
                {
                    id: 56,
                    work_item_id: 103,
                    tooth_number: '21',
                    status: 'in_progress',
                    shade: 'A1',
                    material: 'Porcelain',
                },
            ];

            render(
                <ClinicalChartInspector
                    copy={mockCopy}
                    selection={{ toothKey: '21' }}
                    toothState={mockToothState}
                    labOrders={mockLabOrders}
                    patientId={42}
                />
            );

            expect(screen.queryByTestId('lab-status-badge-103')).not.toBeInTheDocument();
            const metadata = screen.getByTestId('item-shade-material-103');
            expect(metadata).toHaveTextContent('Porcelain');
            expect(metadata).toHaveTextContent(/Shade: A1/i);
        });
    });

    describe('G12-M11: DentalChartSVG Tooth Lab Ready Badge', () => {
        it('renders tooth lab-ready badge for tooth 21 when labStatusByTooth is lab_ready', () => {
            render(
                <DentalChartSVG
                    teethStatus={{}}
                    onToothClick={vi.fn()}
                    isPediatric={false}
                    labStatusByTooth={{ '21': 'lab_ready' }}
                />
            );

            const badge = screen.getByTestId('lab-status-tooth-badge-21');
            expect(badge).toBeInTheDocument();
            expect(badge).toHaveTextContent('LAB READY');

            // Other teeth should not have lab-ready badge
            expect(screen.queryByTestId('lab-status-tooth-badge-11')).not.toBeInTheDocument();
        });

        it('does not render tooth lab-ready badge when tooth is unmapped or absent', () => {
            render(
                <DentalChartSVG
                    teethStatus={{}}
                    onToothClick={vi.fn()}
                    isPediatric={false}
                    labStatusByTooth={{ '21': 'unmapped', '16': 'pending' }}
                />
            );

            expect(screen.queryByTestId('lab-status-tooth-badge-21')).not.toBeInTheDocument();
            expect(screen.queryByTestId('lab-status-tooth-badge-16')).not.toBeInTheDocument();
        });
    });
});
