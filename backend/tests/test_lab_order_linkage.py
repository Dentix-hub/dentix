from backend.routers.laboratories import TREATMENT_LINK_PREFIX, _linked_treatment_stmt


def test_lab_order_treatment_link_uses_exact_marker_not_substring_matching():
    stmt = _linked_treatment_stmt(tenant_id=7, order_id=1)
    compiled = stmt.compile()
    sql = str(compiled)
    params = compiled.params

    assert "treatments.tenant_id =" in sql
    assert "treatments.notes =" in sql
    assert "LIKE" not in sql.upper()
    assert f"{TREATMENT_LINK_PREFIX}1" in params.values()
    assert 7 in params.values()


def test_lab_order_markers_do_not_share_the_same_value_prefix_contract():
    order_one = f"{TREATMENT_LINK_PREFIX}1"
    order_ten = f"{TREATMENT_LINK_PREFIX}10"

    assert order_one != order_ten
    # The old substring query would match this relationship; exact equality does not.
    assert order_one in order_ten
