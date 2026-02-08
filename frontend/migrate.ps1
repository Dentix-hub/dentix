$ErrorActionPreference = "Continue" # Continue so one failure doesn't stop others (e.g. if file already moved)

Write-Host "Creating Directories..."
New-Item -ItemType Directory -Path "src/features/ai", "src/features/lab", "src/features/dental", "src/features/settings", "src/features/admin", "src/shared/ui" -Force

Write-Host "Moving AI..."
Move-Item "src/components/AIChat.jsx", "src/components/AIStats.jsx" "src/features/ai/" -Force

Write-Host "Moving Billing..."
Move-Item "src/components/BillingTabs", "src/components/DoctorRevenue.jsx" "src/features/billing/" -Force

Write-Host "Moving Patients..."
Move-Item "src/components/PatientInfoCard.jsx", "src/components/PatientScanner.jsx", "src/components/PatientTabs" "src/features/patients/" -Force

Write-Host "Moving Lab..."
Move-Item "src/components/LabOrdersTab.jsx" "src/features/lab/" -Force

Write-Host "Moving Dental..."
Move-Item "src/components/DentalChart.jsx", "src/components/DentalChartSVG.jsx" "src/features/dental/" -Force

Write-Host "Moving Settings..."
Move-Item "src/components/SettingsTabs", "src/components/Profile" "src/features/settings/" -Force

Write-Host "Moving Admin..."
Move-Item "src/components/SuperAdmin" "src/features/admin/" -Force

Write-Host "Moving Shared UI..."
Move-Item "src/components/Modal.jsx", "src/components/ConfirmDialog.jsx", "src/components/LoadingSpinner.jsx", "src/components/Skeleton.jsx", "src/components/DataTable.jsx", "src/components/StatCard.jsx", "src/components/NotificationBell.jsx", "src/components/BackgroundWrapper.jsx", "src/components/GlobalBanner.jsx", "src/components/SupportModal.jsx", "src/components/GlobalSearch.jsx" "src/shared/ui/" -Force

Write-Host "Moving Layout..."
Move-Item "src/components/Layout.jsx" "src/layouts/" -Force

Write-Host "Moving Modals..."
Move-Item "src/components/modals" "src/shared/ui/" -Force

Write-Host "Done."
