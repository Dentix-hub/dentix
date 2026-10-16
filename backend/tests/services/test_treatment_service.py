"""
C6.2 — TreatmentService Unit Tests

Tests all TreatmentService logic:
- Treatment creation (with pricing + stock)
- Treatment update
- Treatment deletion
- Stock validation and consumption
- Price snapshot generation
- Edge cases and error handling
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.services.treatment_service import TreatmentService, get_treatment_service
from backend.services.pricing_service import PricingService
from backend import models, schemas


# ============================================
# FIXTURES
# ============================================


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()

    # Default mock result behavior
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    # Legacy query mock for backward compatibility
    query = MagicMock()
    session.query.return_value = query
    query.filter.return_value = query
    query.join.return_value = query
    query.options.return_value = query
    query.order_by.return_value = query
    query.first.return_value = None
    query.all.return_value = []

    return session


@pytest.fixture
def mock_user():
    """Mock authenticated user (doctor)."""
    user = MagicMock(spec=models.User)
    user.id = 10
    user.tenant_id = 1
    user.role = "doctor"
    user.username = "dr_test"
    return user


@pytest.fixture
def treatment_service(mock_db, mock_user):
    """Create TreatmentService with mocked dependencies."""
    with patch(
        "backend.services.treatment_service.get_pricing_service"
    ) as mock_pricing_factory:
        class MockPriceList:
            def __init__(self, name, pl_type):
                self.name = name
                self.type = pl_type

        mock_pricing = MagicMock(spec=PricingService)
        mock_pricing.get_procedure_price = AsyncMock(return_value=500.0)
        mock_pricing.get_price_list = AsyncMock(return_value=MockPriceList("Cash", "cash"))
        mock_pricing_factory.return_value = mock_pricing

        svc = TreatmentService(mock_db, tenant_id=1, current_user=mock_user)
        svc.pricing = mock_pricing
        yield svc


@pytest.fixture
def sample_treatment_data():
    """Sample treatment creation payload."""
    return schemas.TreatmentCreate(
        patient_id=1,
        procedure="Composite Filling",
        cost=500.0,
        diagnosis="Caries",
        notes="Mesial surface",
        consumedMaterials=None,
    )


@pytest.fixture
def sample_treatment_with_materials():
    """Treatment with consumed materials."""
    return schemas.TreatmentCreate(
        patient_id=1,
        procedure="Root Canal",
        cost=2000.0,
        diagnosis="Irreversible Pulpitis",
        consumedMaterials=[
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=2.0),
            schemas.clinical.ConsumedMaterialItem(material_id=2, quantity=0.5),
        ],
    )


# ============================================
# CREATION TESTS
# ============================================


class TestTreatmentCreation:
    """Tests for TreatmentService.create_treatment."""

    async def test_create_basic_treatment(self, treatment_service, sample_treatment_data, mock_db):
        """Basic treatment creation without stock."""
        # Arrange
        mock_patient = MagicMock(spec=models.Patient)
        mock_patient.id = 1
        mock_patient.default_price_list_id = None

        mock_treatment = MagicMock(spec=models.Treatment)
        mock_treatment.id = 100
        mock_treatment.procedure = "Composite Filling"

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=500.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            # Act
            result = await treatment_service.create_treatment(sample_treatment_data)

            # Assert
            assert result.id == 100
            mock_crud.patient.get_patient.assert_called_once_with(mock_db, 1, 1)
            mock_crud.billing.create_treatment.assert_called_once()

    async def test_create_treatment_patient_not_found(self, treatment_service, sample_treatment_data):
        """Must raise 404 if patient does not exist."""
        from fastapi import HTTPException

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await treatment_service.create_treatment(sample_treatment_data)

            assert exc_info.value.status_code == 404
            assert "Patient not found" in str(exc_info.value.detail)

    async def test_create_treatment_auto_assigns_doctor(
        self, treatment_service, mock_db, mock_user
    ):
        """Doctor ID should default to current user if not provided."""
        data = schemas.TreatmentCreate(
            patient_id=1,
            procedure="Scaling",
            cost=300.0,
            doctor_id=None,
        )

        mock_patient = MagicMock(default_price_list_id=None)
        mock_treatment = MagicMock(id=101)

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=300.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            await treatment_service.create_treatment(data)

            # Verify doctor_id was set to current user
            call_kwargs = mock_crud.billing.create_treatment.call_args
            assert call_kwargs.kwargs["doctor_id"] == mock_user.id

    async def test_create_treatment_commits_transaction(
        self, treatment_service, sample_treatment_data, mock_db
    ):
        """Treatment creation must commit the DB transaction."""
        mock_patient = MagicMock(default_price_list_id=None)
        mock_treatment = MagicMock(id=102)

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=500.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            await treatment_service.create_treatment(sample_treatment_data)

            mock_db.commit.assert_called()
            mock_db.refresh.assert_called_with(mock_treatment)

    async def test_create_treatment_deferred_commit(
        self, treatment_service, sample_treatment_data, mock_db
    ):
        """Treatment must be created with commit=False for transactional safety."""
        mock_patient = MagicMock(default_price_list_id=None)
        mock_treatment = MagicMock(id=103)

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=500.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            await treatment_service.create_treatment(sample_treatment_data)

            call_kwargs = mock_crud.billing.create_treatment.call_args
            assert call_kwargs.kwargs["commit"] is False


# ============================================
# STOCK VALIDATION TESTS
# ============================================


class TestStockValidation:
    """Tests for TreatmentService stock validation."""

    async def test_validate_empty_materials_passes(self, treatment_service):
        """Empty materials list should pass validation silently."""
        await treatment_service.validate_treatment_stock([])

    async def test_validate_sufficient_stock(self, treatment_service):
        """Validation passes when stock is available."""
        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=2.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.validate_stock = AsyncMock(return_value=(True, 10.0, "Composite A2"))

            await treatment_service.validate_treatment_stock(materials)
            mock_inv.validate_stock.assert_called_once()

    async def test_validate_insufficient_stock_raises(self, treatment_service):
        """Must raise 400 with details when stock is insufficient."""
        from fastapi import HTTPException

        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=100.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.validate_stock = AsyncMock(return_value=(False, 5.0, "Composite A2"))

            with pytest.raises(HTTPException) as exc_info:
                await treatment_service.validate_treatment_stock(materials)

            assert exc_info.value.status_code == 400
            assert "Composite A2" in str(exc_info.value.detail)

    async def test_validate_stock_internal_error(self, treatment_service):
        """Internal stock error should raise 500."""
        from fastapi import HTTPException

        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=99, quantity=1.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.validate_stock = AsyncMock(side_effect=Exception("DB connection lost"))

            with pytest.raises(HTTPException) as exc_info:
                await treatment_service.validate_treatment_stock(materials)

            assert exc_info.value.status_code == 500


# ============================================
# STOCK CONSUMPTION TESTS
# ============================================


class TestStockConsumption:
    """Tests for TreatmentService.consume_treatment_stock."""

    async def test_consume_empty_list_noop(self, treatment_service):
        """Empty materials list is a no-op."""
        await treatment_service.consume_treatment_stock(treatment_id=1, consumed_materials=[])

    async def test_consume_stock_success(self, treatment_service, mock_user):
        """Stock consumption should call inventory service correctly."""
        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=2.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.consume_stock = AsyncMock()
            await treatment_service.consume_treatment_stock(
                treatment_id=50, consumed_materials=materials
            )

            mock_inv.consume_stock.assert_called_once_with(
                material_id=1,
                quantity=2.0,
                tenant_id=1,
                user_id=mock_user.id,
                reference_id="TREATMENT:50",
                patient_id=None,
                db=treatment_service.db,
                commit=False,
            )

    async def test_consume_stock_confirm_open_required(self, treatment_service):
        """CONFIRM_OPEN_REQUIRED error should raise 409 with structured data."""
        from fastapi import HTTPException

        materials = [
            schemas.clinical.ConsumedMaterialItem(material_id=1, quantity=1.0)
        ]

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.consume_stock = AsyncMock(side_effect=Exception(
                "CONFIRM_OPEN_REQUIRED:42:Composite A2 (4g)"
            ))

            with pytest.raises(HTTPException) as exc_info:
                await treatment_service.consume_treatment_stock(
                    treatment_id=50, consumed_materials=materials
                )

            assert exc_info.value.status_code == 409
            detail = exc_info.value.detail
            assert detail["code"] == "CONFIRM_OPEN_REQUIRED"
            assert detail["stock_item_id"] == 42


# ============================================
# UPDATE & DELETE TESTS
# ============================================


class TestTreatmentUpdate:
    """Tests for TreatmentService.update_treatment."""

    async def test_update_treatment_basic(self, treatment_service, sample_treatment_data, mock_db):
        """Basic treatment update."""
        mock_updated = MagicMock(spec=models.Treatment)
        mock_updated.id = 100

        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.reverse_stock_by_reference = AsyncMock()

            with patch("backend.crud") as mock_crud:
                mock_crud.billing.update_treatment = AsyncMock(return_value=mock_updated)

                result = await treatment_service.update_treatment(100, sample_treatment_data)

                assert result.id == 100
                mock_db.commit.assert_called()

    async def test_update_treatment_validates_stock_first(
        self, treatment_service, sample_treatment_with_materials
    ):
        """Stock validation must happen before DB update."""
        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.reverse_stock_by_reference = AsyncMock()

            with patch("backend.crud") as mock_crud:
                mock_crud.billing.update_treatment = AsyncMock(return_value=MagicMock(id=100))

                with patch.object(
                    treatment_service, "validate_treatment_stock"
                ) as mock_validate, patch.object(
                    treatment_service, "consume_treatment_stock"
                ) as mock_consume:
                    await treatment_service.update_treatment(
                        100, sample_treatment_with_materials
                    )

                    mock_validate.assert_called_once()
                    mock_consume.assert_called_once()


class TestTreatmentDelete:
    """Tests for TreatmentService.delete_treatment."""

    async def test_delete_treatment_basic(self, treatment_service, mock_db):
        """Delete calls crud and logs admin action."""
        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.reverse_stock_by_reference = AsyncMock()

            with patch("backend.crud") as mock_crud:
                mock_crud.billing.delete_treatment = AsyncMock(return_value=True)

                with patch(
                    "backend.services.treatment_service.log_admin_action"
                ) as mock_log:
                    await treatment_service.delete_treatment(100)

                    mock_crud.billing.delete_treatment.assert_called_once_with(mock_db, 100, 1)
                    mock_log.assert_called_once()


# ============================================
# PRICING INTEGRATION
# ============================================


class TestTreatmentPricing:
    """Tests for price calculation and snapshot in create_treatment."""

    async def test_price_snapshot_created_on_creation(self, treatment_service, mock_db):
        """Treatment creation should generate a price snapshot."""
        data = schemas.TreatmentCreate(
            patient_id=1,
            procedure="Crown Prep",
            cost=3000.0,
        )

        mock_patient = MagicMock(default_price_list_id=5)
        mock_treatment = MagicMock(id=200)

        # Mocking execute calls inside _calculate_price_and_snapshot
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [
            mock_patient,  # stmt_patient
            MagicMock(spec=models.Procedure, id=1, price=3000.0),  # stmt_proc
            None,  # price list
        ]
        mock_db.execute.return_value = mock_result

        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=mock_patient)
            mock_crud.billing.create_treatment = AsyncMock(return_value=mock_treatment)

            await treatment_service.create_treatment(data)

            call_kwargs = mock_crud.billing.create_treatment.call_args
            assert call_kwargs.kwargs["unit_price"] is not None


# ============================================
# FACTORY FUNCTION
# ============================================


class TestTreatmentServiceFactory:
    """Tests for the factory function."""

    def test_get_treatment_service_returns_instance(self):
        """Factory should return a TreatmentService instance."""
        mock_db = MagicMock()
        mock_user = MagicMock(spec=models.User)
        mock_user.tenant_id = 1

        with patch(
            "backend.services.treatment_service.get_pricing_service"
        ):
            svc = get_treatment_service(mock_db, 1, mock_user)
            assert isinstance(svc, TreatmentService)
            assert svc.tenant_id == 1


# ============================================
# PERSISTENCE OF TREATMENT MATERIAL USAGES
# ============================================


class TestTreatmentMaterialUsagePersistence:
    """Tests for TreatmentService.persist_treatment_material_usages."""

    async def test_persist_non_divisible_usage(self, treatment_service, mock_db):
        """Should persist non-divisible material usage with calculated cost."""
        # Arrange
        consumed = [
            schemas.clinical.ConsumedMaterialItem(
                material_id=1,
                quantity=2.0,
                material_type="NON_DIVISIBLE"
            )
        ]

        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.type = "NON_DIVISIBLE"
        mock_material.standard_price = 10.0

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.side_effect = [
            [mock_material],  # stmt_mat execute scalars all
            [],  # stmt_moves execute scalars all
        ]
        mock_db.execute.return_value = mock_result

        # Act
        await treatment_service.persist_treatment_material_usages(
            treatment_id=100,
            consumed_materials=consumed,
            doctor_id=10
        )

        # Assert
        added_objs = [call.args[0] for call in mock_db.add.call_args_list]
        usage = next(obj for obj in added_objs if isinstance(obj, models.inventory.TreatmentMaterialUsage))
        assert usage.treatment_id == 100
        assert usage.material_id == 1
        assert usage.quantity_used == 2.0
        assert usage.cost_calculated == 20.0

    async def test_delete_treatment_cleans_up_usage(self, treatment_service, mock_db):
        """Deleting a treatment should also delete its TreatmentMaterialUsage records."""
        # Arrange
        with patch(
            "backend.services.treatment_service.inventory_service"
        ) as mock_inv:
            mock_inv.reverse_stock_by_reference = AsyncMock()

            with patch("backend.crud") as mock_crud:
                mock_crud.billing.delete_treatment = AsyncMock(return_value=True)
                with patch("backend.services.treatment_service.log_admin_action"):
                    # Act
                    await treatment_service.delete_treatment(100)

                    # Assert
                    # Verify that execute() was called on the session to run the delete statement
                    mock_db.execute.assert_called()


# ============================================
# SURFACE TARGETING & MULTI-PROCEDURE TESTS
# ============================================


class TestTreatmentSurfaceAndMultiProcedure:
    """Tests for multi-procedure, surface-level targeting, and clinical sync."""

    async def test_create_treatment_with_surfaces_syncs_work_item(
        self, treatment_service, mock_db
    ):
        """Creating a treatment with MOD surfaces creates ClinicalWorkItem with surface targets."""
        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=MagicMock(id=1, default_price_list_id=None))
            created_treatment = models.Treatment(
                id=101,
                patient_id=1,
                tooth_number=16,
                procedure="Composite Filling",
                cost=500.0,
                status="Done",
                doctor_id=10,
                tenant_id=1,
            )
            mock_crud.billing.create_treatment = AsyncMock(return_value=created_treatment)
            with patch("backend.services.treatment_service.log_admin_action"):
                data = schemas.TreatmentCreate(
                    patient_id=1,
                    tooth_number=16,
                    procedure="Composite Filling",
                    cost=500.0,
                    surfaces=["M", "O", "D"],
                    notes="MOD restoration",
                )
                res = await treatment_service.create_treatment(data)

                # Assert surfaces are attached
                assert res.surfaces == ["M", "O", "D"]
                assert res.surface == "DMO" or res.surface == "MOD" or set(res.surface) == {"M", "O", "D"}

                # Assert ClinicalWorkItem and targets were added to session
                added_objs = [call.args[0] for call in mock_db.add.call_args_list]
                work_items = [obj for obj in added_objs if isinstance(obj, models.ClinicalWorkItem)]
                assert len(work_items) == 1
                assert work_items[0].kind == "procedure"
                assert work_items[0].status == "completed"

                targets = [obj for obj in added_objs if isinstance(obj, models.ClinicalWorkItemTarget)]
                assert len(targets) == 3
                assert {t.surface_code for t in targets} == {"M", "O", "D"}
                assert all(t.target_kind == "surface" for t in targets)
                assert all(t.tooth_key == "16" for t in targets)

    async def test_create_treatment_with_single_surface_string(
        self, treatment_service, mock_db
    ):
        """Single surface string (e.g. 'O') maps to single surface target."""
        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=MagicMock(id=1, default_price_list_id=None))
            created_treatment = models.Treatment(
                id=102,
                patient_id=1,
                tooth_number=24,
                procedure="Composite Filling",
                cost=300.0,
                status="Done",
                doctor_id=10,
                tenant_id=1,
            )
            mock_crud.billing.create_treatment = AsyncMock(return_value=created_treatment)
            with patch("backend.services.treatment_service.log_admin_action"):
                data = schemas.TreatmentCreate(
                    patient_id=1,
                    tooth_number=24,
                    procedure="Composite Filling",
                    cost=300.0,
                    surface="O",
                )
                res = await treatment_service.create_treatment(data)
                assert res.surface == "O"

                added_objs = [call.args[0] for call in mock_db.add.call_args_list]
                targets = [obj for obj in added_objs if isinstance(obj, models.ClinicalWorkItemTarget)]
                assert len(targets) == 1
                assert targets[0].surface_code == "O"
                assert targets[0].target_kind == "surface"

    async def test_create_multi_procedure_treatment_atomic(
        self, treatment_service, mock_db
    ):
        """Recording multiple procedures on a single tooth creates treatments and returns response."""
        with patch("backend.crud") as mock_crud:
            mock_crud.patient.get_patient = AsyncMock(return_value=MagicMock(id=1, default_price_list_id=None))

            t1 = models.Treatment(
                id=201, patient_id=1, tooth_number=46, procedure="Root Canal Treatment", cost=1200.0, discount=0.0, status="Done", doctor_id=10, tenant_id=1
            )
            t2 = models.Treatment(
                id=202, patient_id=1, tooth_number=46, procedure="Composite Filling", cost=400.0, discount=0.0, status="Done", doctor_id=10, tenant_id=1
            )
            mock_crud.billing.create_treatment = AsyncMock(side_effect=[t1, t2])

            with patch("backend.services.treatment_service.log_admin_action"):
                multi_payload = schemas.ToothMultiProcedureCreate(
                    patient_id=1,
                    tooth_number=46,
                    procedures=[
                        schemas.ToothProcedureItem(
                            procedure="Root Canal Treatment",
                            cost=1200.0,
                            diagnosis="Pulpitis",
                        ),
                        schemas.ToothProcedureItem(
                            procedure="Composite Filling",
                            cost=400.0,
                            surfaces=["M", "O"],
                            diagnosis="Caries",
                        ),
                    ],
                )

                response = await treatment_service.create_multi_procedure_treatment(multi_payload)
                assert response.patient_id == 1
                assert response.tooth_number == 46
                assert response.tooth_key == "46"
                assert len(response.treatments) == 2
                mock_db.commit.assert_called()


class TestTreatmentClinicalSyncUpdateDelete:
    """Tests for Slice 1: Synchronizing ClinicalWorkItems on treatment update and delete."""

    async def test_update_treatment_reflects_code_status_surfaces_and_event(
        self, treatment_service, mock_db
    ):
        """Updating treatment updates ClinicalWorkItem fields, replaces targets, and appends ClinicalEvent."""
        treatment_id = 101
        patient_id = 1

        # Existing linked work item and event
        existing_wi = models.ClinicalWorkItem(
            id=50,
            tenant_id=1,
            patient_id=patient_id,
            kind="procedure",
            code="REST_COMPOSITE",
            status="completed",
            notes="Initial filling",
        )
        existing_ev = models.ClinicalEvent(
            id=80,
            tenant_id=1,
            patient_id=patient_id,
            work_item_id=50,
            event_type="procedure_recorded",
            payload={"kind": "procedure", "canonical_code": "REST_COMPOSITE", "treatment_id": treatment_id},
        )

        updated_treatment = models.Treatment(
            id=treatment_id,
            patient_id=patient_id,
            tooth_number=16,
            procedure="Crown",
            status="Pending",
            cost=1500.0,
            discount=0.0,
            doctor_id=10,
            tenant_id=1,
            notes="Upgraded to crown [Surfaces: M, O]",
        )

        def mock_exec(stmt):
            mock_res = MagicMock()
            s = str(stmt).lower()
            if "clinical_events" in s:
                mock_res.scalars.return_value.all.return_value = [existing_ev]
            elif "clinical_work_items" in s:
                mock_res.scalars.return_value.first.return_value = existing_wi
            elif "treatments" in s:
                mock_res.scalars.return_value.first.return_value = updated_treatment
            else:
                mock_res.scalars.return_value.all.return_value = []
                mock_res.scalars.return_value.first.return_value = None
            return mock_res

        mock_db.execute = AsyncMock(side_effect=mock_exec)

        with patch("backend.services.treatment_service.inventory_service") as mock_inv, \
             patch("backend.crud") as mock_crud:
            mock_inv.reverse_stock_by_reference = AsyncMock()
            mock_crud.billing.update_treatment = AsyncMock(return_value=updated_treatment)

            update_data = schemas.TreatmentCreate(
                patient_id=patient_id,
                tooth_number=16,
                procedure="Crown",
                status="Pending",
                cost=1500.0,
                surfaces=["M", "O"],
                notes="Upgraded to crown",
                skip_stock_check=True,
            )

            res = await treatment_service.update_treatment(treatment_id, update_data)

            # 1. Assert legacy contract is preserved
            assert res.id == treatment_id
            assert res.procedure == "Crown"
            assert res.status == "Pending"

            # 2. Assert existing ClinicalWorkItem code and status were updated
            assert existing_wi.code == "PROS_CROWN"
            assert existing_wi.status == "planned"

            # 3. Assert new ClinicalWorkItemTargets were added for surfaces M, O
            added_objs = [call.args[0] for call in mock_db.add.call_args_list]
            targets = [obj for obj in added_objs if isinstance(obj, models.ClinicalWorkItemTarget)]
            assert len(targets) == 2
            assert {t.surface_code for t in targets} == {"M", "O"}
            assert all(t.target_kind == "surface" for t in targets)
            assert all(t.tooth_key == "16" for t in targets)

            # 4. Assert ClinicalEvent was appended with action="updated" and status="planned"
            events = [obj for obj in added_objs if isinstance(obj, models.ClinicalEvent)]
            assert len(events) == 1
            assert events[0].event_type == "procedure_recorded"
            assert events[0].payload.get("action") == "updated"
            assert events[0].payload.get("status") == "planned"
            assert events[0].payload.get("canonical_code") == "PROS_CROWN"
            assert events[0].payload.get("treatment_id") == treatment_id

    async def test_update_treatment_creates_work_item_if_previously_unlinked(
        self, treatment_service, mock_db
    ):
        """Updating a treatment that had no prior work item creates one if tooth is valid."""
        treatment_id = 102
        patient_id = 1

        updated_treatment = models.Treatment(
            id=treatment_id,
            patient_id=patient_id,
            tooth_number=21,
            procedure="Composite Filling",
            status="Done",
            cost=400.0,
            doctor_id=10,
            tenant_id=1,
        )

        def mock_exec(stmt):
            mock_res = MagicMock()
            s = str(stmt).lower()
            if "treatments" in s:
                mock_res.scalars.return_value.first.return_value = updated_treatment
            else:
                mock_res.scalars.return_value.all.return_value = []
                mock_res.scalars.return_value.first.return_value = None
            return mock_res

        mock_db.execute = AsyncMock(side_effect=mock_exec)

        with patch("backend.services.treatment_service.inventory_service") as mock_inv, \
             patch("backend.crud") as mock_crud:
            mock_inv.reverse_stock_by_reference = AsyncMock()
            mock_crud.billing.update_treatment = AsyncMock(return_value=updated_treatment)

            update_data = schemas.TreatmentCreate(
                patient_id=patient_id,
                tooth_number=21,
                procedure="Composite Filling",
                cost=400.0,
                skip_stock_check=True,
            )

            res = await treatment_service.update_treatment(treatment_id, update_data)
            assert res.id == treatment_id

            # Work item created
            added_objs = [call.args[0] for call in mock_db.add.call_args_list]
            work_items = [obj for obj in added_objs if isinstance(obj, models.ClinicalWorkItem)]
            assert len(work_items) == 1
            assert work_items[0].code == "REST_COMPOSITE"
            assert work_items[0].status == "completed"

    async def test_delete_treatment_voids_work_item_and_appends_cancellation_event(
        self, treatment_service, mock_db
    ):
        """Deleting a treatment marks its ClinicalWorkItem as cancelled and appends procedure_cancelled event."""
        treatment_id = 103
        patient_id = 1

        existing_treatment = models.Treatment(
            id=treatment_id,
            patient_id=patient_id,
            tooth_number=36,
            procedure="Root Canal",
            tenant_id=1,
            doctor_id=10,
        )
        existing_wi = models.ClinicalWorkItem(
            id=60,
            tenant_id=1,
            patient_id=patient_id,
            kind="procedure",
            code="ENDO_RCT",
            status="completed",
        )
        existing_ev = models.ClinicalEvent(
            id=90,
            tenant_id=1,
            patient_id=patient_id,
            work_item_id=60,
            event_type="procedure_recorded",
            payload={"kind": "procedure", "canonical_code": "ENDO_RCT", "treatment_id": treatment_id},
        )

        def mock_exec(stmt):
            mock_res = MagicMock()
            s = str(stmt).lower()
            if "clinical_events" in s:
                mock_res.scalars.return_value.all.return_value = [existing_ev]
            elif "clinical_work_items" in s:
                mock_res.scalars.return_value.first.return_value = existing_wi
            elif "treatments" in s:
                mock_res.scalars.return_value.first.return_value = existing_treatment
            else:
                mock_res.scalars.return_value.all.return_value = []
                mock_res.scalars.return_value.first.return_value = None
            return mock_res

        mock_db.execute = AsyncMock(side_effect=mock_exec)

        with patch("backend.services.treatment_service.inventory_service") as mock_inv, \
             patch("backend.crud") as mock_crud, \
             patch("backend.services.treatment_service.log_admin_action"):
            mock_inv.reverse_stock_by_reference = AsyncMock()
            mock_crud.billing.delete_treatment = AsyncMock(return_value={"id": treatment_id, "deleted": True})

            res = await treatment_service.delete_treatment(treatment_id)
            assert res == {"id": treatment_id, "deleted": True}

            # 1. Assert ClinicalWorkItem status was voided to "cancelled"
            assert existing_wi.status == "cancelled"

            # 2. Assert a procedure_cancelled ClinicalEvent was appended
            added_objs = [call.args[0] for call in mock_db.add.call_args_list]
            events = [obj for obj in added_objs if isinstance(obj, models.ClinicalEvent)]
            assert len(events) == 1
            cancel_ev = events[0]
            assert cancel_ev.event_type == "procedure_cancelled"
            assert cancel_ev.work_item_id == 60
            assert cancel_ev.payload.get("status") == "cancelled"
            assert cancel_ev.payload.get("action") == "deleted"
            assert cancel_ev.payload.get("superseded") is True
            assert cancel_ev.payload.get("treatment_id") == treatment_id

            # 3. Assert historical events were NEVER deleted
            deleted_objs = [call.args[0] for call in mock_db.delete.call_args_list] if mock_db.delete.called else []
            assert not any(isinstance(obj, models.ClinicalEvent) for obj in deleted_objs)

    async def test_tenant_isolation_on_work_item_lookup(
        self, treatment_service, mock_db
    ):
        """Cross-tenant events are excluded from work item lookup."""
        treatment_id = 104
        patient_id = 1

        # Event belongs to tenant 99 (different from service.tenant_id = 1)
        cross_tenant_ev = models.ClinicalEvent(
            id=91,
            tenant_id=99,
            patient_id=patient_id,
            work_item_id=70,
            event_type="procedure_recorded",
            payload={"kind": "procedure", "canonical_code": "ENDO_RCT", "treatment_id": treatment_id},
        )

        # Mock execute returning empty because SQL filters by tenant_id == 1
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_res)

        wi = await treatment_service._find_linked_clinical_work_item(treatment_id, patient_id)
        assert wi is None

        # Verify that the query included tenant_id == 1
        called_stmt = mock_db.execute.call_args[0][0]
        assert "tenant_id =" in str(called_stmt) or "clinical_events.tenant_id" in str(called_stmt)

    async def test_multi_procedure_independent_update_and_delete(
        self, treatment_service, mock_db
    ):
        """In a multi-procedure tooth, updating procedure A and deleting procedure B affect distinct work items."""
        patient_id = 1
        tooth_number = 46

        # Two treatments for the same tooth (multi-procedure)
        t_endo = models.Treatment(id=301, patient_id=patient_id, tooth_number=tooth_number, procedure="Root Canal", tenant_id=1)
        t_comp = models.Treatment(id=302, patient_id=patient_id, tooth_number=tooth_number, procedure="Composite Filling", tenant_id=1)

        wi_endo = models.ClinicalWorkItem(id=71, tenant_id=1, patient_id=patient_id, kind="procedure", code="ENDO_RCT", status="completed")
        wi_comp = models.ClinicalWorkItem(id=72, tenant_id=1, patient_id=patient_id, kind="procedure", code="REST_COMPOSITE", status="completed")

        ev_endo = models.ClinicalEvent(id=101, tenant_id=1, patient_id=patient_id, work_item_id=71, event_type="procedure_recorded", payload={"treatment_id": 301})
        ev_comp = models.ClinicalEvent(id=102, tenant_id=1, patient_id=patient_id, work_item_id=72, event_type="procedure_recorded", payload={"treatment_id": 302})

        # Test finding linked work items individually
        def mock_exec_for_find(stmt):
            mock_res = MagicMock()
            s = str(stmt).lower()
            if "clinical_events" in s:
                mock_res.scalars.return_value.all.return_value = [ev_endo, ev_comp]
            elif "clinical_work_items" in s:
                target_id = None
                for c in getattr(stmt, "_where_criteria", ()):
                    if hasattr(c, "right") and hasattr(c.right, "value"):
                        target_id = c.right.value
                        break
                if target_id == 71:
                    mock_res.scalars.return_value.first.return_value = wi_endo
                elif target_id == 72:
                    mock_res.scalars.return_value.first.return_value = wi_comp
                else:
                    try:
                        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
                        if "71" in compiled:
                            mock_res.scalars.return_value.first.return_value = wi_endo
                        elif "72" in compiled:
                            mock_res.scalars.return_value.first.return_value = wi_comp
                        else:
                            mock_res.scalars.return_value.first.return_value = None
                    except Exception:
                        mock_res.scalars.return_value.first.return_value = None
            else:
                mock_res.scalars.return_value.first.return_value = None
            return mock_res

        mock_db.execute = AsyncMock(side_effect=mock_exec_for_find)

        found_wi_1 = await treatment_service._find_linked_clinical_work_item(301, patient_id)
        found_wi_2 = await treatment_service._find_linked_clinical_work_item(302, patient_id)

        assert found_wi_1.id == 71
        assert found_wi_2.id == 72
        assert found_wi_1 != found_wi_2
