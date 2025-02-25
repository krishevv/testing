from src.database import Base, get_db
from src.main import app

import sys
import os
import json
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Создаем in‑memory SQLite базу для тестов с использованием StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Фикстура для тестовой базы
@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown():
    Base.metadata.drop_all(bind=engine)  # Очистка базы
    Base.metadata.create_all(bind=engine)  # Создание новой
    yield


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# Подменяем зависимость в FastAPI
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_add_molecule():
    response = client.post("/add", json={"structure": "CCO"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("message") == "Молекула добавлена"
    assert "id" in data


def test_get_molecule():
    add_response = client.post("/add", json={"structure": "CCO"})
    mol_id = add_response.json()["id"]
    response = client.get(f"/molecule/{mol_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == mol_id
    assert data["structure"] == "CCO"


def test_update_molecule():
    add_response = client.post("/add", json={"structure": "CCO"})
    mol_id = add_response.json()["id"]
    update_response = client.put(f"/molecule/{mol_id}", json={"structure": "CCC"})
    assert update_response.status_code == 200
    update_data = update_response.json()
    assert update_data.get("message") == "Молекула обновлена успешно"
    assert update_data["id"] == mol_id
    get_response = client.get(f"/molecule/{mol_id}")
    get_data = get_response.json()
    assert get_data["structure"] == "CCC"


def test_delete_molecule():
    add_response = client.post("/add", json={"structure": "CCO"})
    mol_id = add_response.json()["id"]
    delete_response = client.delete(f"/molecule/{mol_id}")
    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data.get("message") == "Молекула удалена"
    assert delete_data["id"] == mol_id
    get_response = client.get(f"/molecule/{mol_id}")
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Молекула не найдена"


def test_search_substructure():
    client.post("/add", json={"structure": "CCO"})
    response = client.post("/search", json={"substructure": "CO"})
    assert response.status_code == 200
    data = response.json()
    matches = data.get("matches", [])
    assert any(match.get("smiles") == "CCO" for match in matches)


def test_upload_molecules():
    molecules = [
        {"structure": "CCN"},
        {"structure": "OCC"}
    ]
    data_json = json.dumps(molecules)
    files = {
        "file": ("molecules.json", BytesIO(data_json.encode()), "application/json")
    }
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data.get("message") == "Молекулы успешно загружены."
    assert data.get("count") == len(molecules)


def test_search_substructure_invalid():
    # Отправляем невалидную SMILES для подструктуры
    response = client.post("/search", json={"substructure": "invalid_smiles"})
    assert response.status_code == 400
    data = response.json()
    assert "Некорректный SMILES" in data["detail"]


def test_upload_invalid_file_type():
    # Передаём файл не с JSON MIME типом
    files = {
        "file": ("test.txt", BytesIO(b"not a json"), "text/plain")
    }
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Только JSON-файлы поддерживаются."


def test_upload_missing_structure():
    # Отправляем JSON с объектом, где отсутствует ключ 'structure'
    data_json = json.dumps([{"not_structure": "CCN"}])
    files = {
        "file": ("molecules.json", BytesIO(data_json.encode()), "application/json")
    }
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    data = response.json()
    # Ожидаем сообщение об отсутствии поля 'structure'
    assert "Каждый объект должен содержать поле" in data["detail"]


def test_upload_invalid_smiles():
    # Отправляем JSON с одним валидным и одним невалидным SMILES
    data_json = json.dumps([
        {"structure": "CCN"},
        {"structure": "invalid"}
    ])
    files = {
        "file": ("molecules.json", BytesIO(data_json.encode()), "application/json")
    }
    response = client.post("/upload", files=files)
    assert response.status_code == 400
    data = response.json()
    # Ожидаем сообщение о невалидном SMILES
    assert "Некорректный SMILES" in data["detail"]


def test_root_endpoint():
    # Проверяем, что корневой эндпоинт возвращает server_id
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "server_id" in data
