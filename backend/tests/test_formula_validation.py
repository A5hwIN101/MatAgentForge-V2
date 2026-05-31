import pytest

from app.graph.workflow import InvalidMaterialFormulaError, validate_material_formula


def test_rejects_leading_zero_formula() -> None:
    with pytest.raises(InvalidMaterialFormulaError):
        validate_material_formula("LiCo02")


def test_rejects_dummy_species_formula() -> None:
    with pytest.raises(InvalidMaterialFormulaError):
        validate_material_formula("XYZ123")


def test_normalizes_grouped_transition_metal_formula() -> None:
    normalized = validate_material_formula("Li(Ni,Mn,Co)O2")
    assert normalized == "LiNiMnCoO2"
