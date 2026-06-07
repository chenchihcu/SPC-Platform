from app.data.repositories import InMemoryRepository
from app.viewmodels.coordinate_manager_viewmodel import CoordinateManagerViewModel
from app.viewmodels.main_viewmodel import MainViewModel
from app.viewmodels.workorder_viewmodel import WorkorderViewModel


def test_inmemory_repository_returns_copy() -> None:
    repo = InMemoryRepository()
    repo.add({"id": 1})
    out = repo.list_all()
    assert out == [{"id": 1}]
    out.append({"id": 2})
    assert repo.list_all() == [{"id": 1}]


def test_basic_viewmodels_have_mutable_state_dict() -> None:
    for vm in (MainViewModel(), WorkorderViewModel(), CoordinateManagerViewModel()):
        assert isinstance(vm.state, dict)
        vm.state["ok"] = True
        assert vm.state["ok"] is True
