import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import get_db, Base
from src.main import app
import json
from io import BytesIO
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Создаем тестовую БД
TEST_DATABASE_URL = "sqlite:///test_db.sqlite"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown():
    """Создает таблицы перед каждым тестом и очищает после."""
    Base.metadata.drop_all(bind=engine)  # Чистим БД перед каждым тестом
    Base.metadata.create_all(bind=engine)  # Пересоздаем таблицы


def override_get_db():
    """Заменяем БД на тестовую."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Подключаем тестовую БД
app.dependency_overrides[get_db] = override_get_db
print("База подключена к клиенту:", app.dependency_overrides[get_db])
client = TestClient(app)
Base.metadata.drop_all(bind=engine)


def test_full_molecule_flow():
    """Полный сценарий работы с молекулой."""
    # 1. Добавляем молекулу
    add_response = client.post("/add", json={"structure": "CCO"})
    assert add_response.status_code == 200
    mol_id = add_response.json()["id"]

    # 2. Проверяем, что молекула есть в списке
    list_response = client.get("/list")
    assert list_response.status_code == 200
    molecules = [m["id"] for m in list_response.json()]
    assert mol_id in molecules

    # 3. Ищем молекулу по подструктуре
    search_response = client.post("/search", json={"substructure": "CO"})
    assert search_response.status_code == 200
    matches = search_response.json().get("matches", [])
    assert any(match.get("id") == mol_id for match in matches)

    # 4. Обновляем молекулу
    update_response = client.put(f"/molecule/{mol_id}", json={"structure": "CCC"})
    assert update_response.status_code == 200
    assert update_response.json().get("message") == "Молекула обновлена успешно"

    # 5. Проверяем, что обновление применилось
    get_response = client.get(f"/molecule/{mol_id}")
    assert get_response.status_code == 200
    assert get_response.json()["structure"] == "CCC"

    # 6. Удаляем молекулу
    delete_response = client.delete(f"/molecule/{mol_id}")
    assert delete_response.status_code == 200

    # 7. Проверяем, что молекулы больше нет
    list_response = client.get("/list")
    assert list_response.status_code == 200
    molecules = [m["id"] for m in list_response.json()]
    assert mol_id not in molecules  # Должно быть True


def test_upload_and_search():
    # Загружаем JSON-файл с молекулами
    molecules = [{"structure": "CCN"}, {"structure": "OCC"}]
    data_json = json.dumps(molecules)
    files = {"file": ("molecules.json",
                      BytesIO(data_json.encode()),
                      "application/json")}
    upload_response = client.post("/upload", files=files)
    assert upload_response.status_code == 200
    assert upload_response.json().get("count") == len(molecules)

    # Ищем загруженную молекулу
    search_response = client.post("/search", json={"substructure": "CC"})
    assert search_response.status_code == 200
    matches = search_response.json().get("matches", [])
    assert len(matches) > 0


def test_delete_nonexistent_molecule():
    # Пытаемся удалить несуществующую молекулу
    delete_response = client.delete("/molecule/9999")
    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "Молекула не найдена"


def test_update_nonexistent_molecule():
    """Проверяет, что обновление несуществующей молекулы возвращает 404."""
    update_response = client.put("/molecule/9999", json={"structure": "CCC"})
    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Молекула не найдена"


def test_search_invalid_smiles():
    # Поиск с некорректным SMILES
    response = client.post("/search", json={"substructure": "invalid_smiles"})
    assert response.status_code == 400
    assert "Некорректный SMILES" in response.json()["detail"]


def test_list_after_deleting_all():
    """После удаления всех молекул список должен быть пустым."""
    # Добавляем молекулу
    add_response = client.post("/add", json={"structure": "CCO"})
    assert add_response.status_code == 200
    mol_id = add_response.json()["id"]

    # Удаляем
    delete_response = client.delete(f"/molecule/{mol_id}")
    assert delete_response.status_code == 200

    # Проверяем список
    list_response = client.get("/list")
    assert list_response.status_code == 200
    assert list_response.json() == []  # Должен быть пустым


def test_upload_multiple_and_search():
    """Загрузка нескольких молекул и их поиск по подструктуре"""
    molecules = [{"structure": "CCN"}, {"structure": "OCC"}, {"structure": "CCO"}]
    data_json = json.dumps(molecules)
    files = {"file": ("molecules.json",
                      BytesIO(data_json.encode()),
                      "application/json")}

    upload_response = client.post("/upload", files=files)
    assert upload_response.status_code == 200
    assert upload_response.json()["count"] == len(molecules)

    # Проверяем поиск
    search_response = client.post("/search", json={"substructure": "CC"})
    assert search_response.status_code == 200
    matches = search_response.json().get("matches", [])
    assert len(matches) == 3  # Должен найти три молекулы с "CC"


def test_upload_empty_file():
    """Проверяет, что загрузка пустого JSON-файла возвращает ошибку."""
    files = {"file": ("empty.json", BytesIO(b""), "application/json")}
    upload_response = client.post("/upload", files=files)
    assert upload_response.status_code == 400
    assert "Файл пуст" in upload_response.json()["detail"]


def test_search_no_results():
    """Проверяет, что если подструктура не найдена, возвращается пустой список."""
    add_response = client.post("/add", json={"structure": "CCO"})
    assert add_response.status_code == 200

    search_response = client.post("/search",
                                  json={"substructure": "CCCC"})  # Нет совпадений
    assert search_response.status_code == 200
    assert search_response.json().get("matches") == []
