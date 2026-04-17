from backend.services.cost_engine import CostEngine
from backend.models.inventory import StockItem, Batch, Material, ProcedureMaterialWeight
from backend.models.clinical import Procedure


class MockDB:
    def __init__(self):
        self.stock_items = []
        self.material_weights = []
        self.procedures = []
        self.current_model = None

    def query(self, *args):
        # Infer model from first arg
        first_arg = args[0]
        # Rough heuristic for mock
        if hasattr(first_arg, "quantity") and hasattr(first_arg, "batch"):  # StockItem
            self.current_model = StockItem
            self.is_complex_query = True
        elif first_arg is Procedure:
            self.current_model = Procedure
            self.is_complex_query = False
        elif first_arg is ProcedureMaterialWeight:
            self.current_model = ProcedureMaterialWeight
            self.is_complex_query = False
        else:
            self.current_model = first_arg  # Fallback
            self.is_complex_query = False
        return self

    def join(self, *args):
        return self

    def options(self, *args):
        return self

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def all(self):
        if self.current_model is StockItem:
            if hasattr(self, "is_complex_query") and self.is_complex_query:
                # Return specialized row objects for the cost engine query
                class MockRow:
                    def __init__(self, item):
                        self.quantity = item.quantity
                        self.cost_per_unit = item.batch.cost_per_unit

                return [MockRow(item) for item in self.stock_items]
            return self.stock_items
        if self.current_model is ProcedureMaterialWeight:
            return self.material_weights
        if self.current_model is Procedure:
            return self.procedures
        return []

    def first(self):
        items = self.all()
        return items[0] if items else None


def test_calculate_bom_cost():
    # Setup
    db = MockDB()
    engine = CostEngine(db, tenant_id=1)

    # Mock Data
    mat1 = Material(id=1, name="Resin", base_unit="g")
    batch1 = Batch(id=101, material_id=1, cost_per_unit=10.0)  # $10/g
    stock1 = StockItem(id=1, batch=batch1, quantity=100)

    mat2 = Material(id=2, name="Bond", base_unit="ml")
    batch2 = Batch(id=102, material_id=2, cost_per_unit=50.0)  # $50/ml
    stock2 = StockItem(id=2, batch=batch2, quantity=10)

    db.stock_items = [stock1, stock2]

    # Procedure Definition (BOM)
    # Uses 2g of Resin and 0.5ml of Bond
    # current_average_usage is the AI-learned actual usage
    bom = [
        ProcedureMaterialWeight(
            material_id=1, weight=2.0, tenant_id=1, procedure_id=1,
            current_average_usage=2.0, sample_size=10,
        ),
        ProcedureMaterialWeight(
            material_id=2, weight=0.5, tenant_id=1, procedure_id=1,
            current_average_usage=0.5, sample_size=10,
        ),
    ]
    # Attach material reference for joinedload mock
    bom[0].material = mat1
    bom[1].material = mat2
    db.material_weights = bom

    # Mock Procedure
    proc = Procedure(id=1, name="Composite Filling", price=100.0)
    db.procedures = [proc]

    # Execution
    # Mock the internal method to return known costs

    def mock_get_avg(material_id):
        if material_id == 1:
            return 10.0  # Resin
        if material_id == 2:
            return 50.0  # Bond
        return 0.0

    engine.get_material_average_cost = mock_get_avg

    # Expected: actual_usage * unit_cost for each
    # (2.0 * 10) + (0.5 * 50) = 20 + 25 = 45.0
    result = engine.calculate_procedure_cost(procedure_id=1)

    if "error" in result:
        raise ValueError(f"Calculation Error: {result['error']}")

    cost = result["total_estimated_cost"]

    # Verification
    print(f"Calculated Cost: ${cost}")
    assert cost == 45.0, f"Expected 45.0, got {cost}"


if __name__ == "__main__":
    try:
        test_calculate_bom_cost()
        print("✅ Cost Calculation Test Passed!")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback

        traceback.print_exc()
