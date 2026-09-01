import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
from decimal import Decimal

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.produit_assurance import ProduitAssurance
from app.models.projet_voyage import ProjetVoyage
from app.models.hospital import Hospital
from app.core.enums import StatutProjetVoyage
from app.core.enums import Role, StatutProjetVoyage, CleRepartition
from app.core.security import get_password_hash


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role=Role.USER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    """Create a test admin user"""
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        role=Role.ADMIN,
        is_active=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_sos_operator(db):
    """Create a test SOS operator"""
    operator = User(
        email="sos@example.com",
        username="sosoperator",
        hashed_password=get_password_hash("sospassword123"),
        full_name="SOS Operator",
        role=Role.SOS_OPERATOR,
        is_active=True
    )
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator


@pytest.fixture
def test_doctor(db):
    """Create a test doctor"""
    doctor = User(
        email="doctor@example.com",
        username="doctor",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Doctor User",
        role=Role.MEDECIN_REFERENT_MH,
        is_active=True
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


@pytest.fixture
def test_receptionist(db):
    """Create a test hospital receptionist"""
    receptionist = User(
        email="reception@example.com",
        username="reception",
        hashed_password=get_password_hash("reception123"),
        full_name="Reception User",
        role=Role.AGENT_RECEPTION_HOPITAL,
        is_active=True
    )
    db.add(receptionist)
    db.commit()
    db.refresh(receptionist)
    return receptionist


@pytest.fixture
def hospital_doctor(db, test_hospital):
    """Médecin rattaché à un hôpital."""
    doctor = User(
        email="hospital.doc@example.com",
        username="hospital_doc",
        hashed_password=get_password_hash("docpassword123"),
        full_name="Médecin Hôpital",
        role=Role.DOCTOR,
        hospital_id=test_hospital.id,
        is_active=True
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


@pytest.fixture
def hospital_referent(db, test_hospital):
    referent = User(
        email="referent@example.com",
        username="hospital_referent",
        hashed_password=get_password_hash("referent123"),
        full_name="Médecin Référent",
        role=Role.MEDECIN_REFERENT_MH,
        hospital_id=test_hospital.id,
        is_active=True,
    )
    db.add(referent)
    db.commit()
    db.refresh(referent)
    return referent


@pytest.fixture
def hospital_accountant(db, test_hospital):
    accountant = User(
        email="accountant@example.com",
        username="hospital_accountant",
        hashed_password=get_password_hash("account123"),
        full_name="Agent Comptable Hôpital",
        role=Role.AGENT_COMPTABLE_HOPITAL,
        hospital_id=test_hospital.id,
        is_active=True,
    )
    db.add(accountant)
    db.commit()
    db.refresh(accountant)
    return accountant


@pytest.fixture
def test_product(db):
    """Create a test insurance product"""
    def _create_product(db_session, **kwargs):
        product = ProduitAssurance(
            code=kwargs.get("code", "TEST-PROD-001"),
            nom=kwargs.get("nom", "Test Insurance Product"),
            description=kwargs.get("description", "Test product description"),
            cout=kwargs.get("cout", Decimal("100.00")),
            cle_repartition=kwargs.get("cle_repartition", CleRepartition.FIXE),
            est_actif=kwargs.get("est_actif", True),
            duree_validite_jours=kwargs.get("duree_validite_jours", 30)
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product
    return _create_product


@pytest.fixture
def test_project(db, test_user):
    """Create a test travel project"""
    def _create_project(db_session, user=None, **kwargs):
        project = ProjetVoyage(
            user_id=user.id if user else test_user.id,
            titre=kwargs.get("titre", "Test Travel Project"),
            description=kwargs.get("description", "Test project description"),
            destination=kwargs.get("destination", "Paris, France"),
            date_depart=kwargs.get("date_depart", datetime.utcnow() + timedelta(days=30)),
            date_retour=kwargs.get("date_retour", datetime.utcnow() + timedelta(days=60)),
            nombre_participants=kwargs.get("nombre_participants", 1),
            statut=kwargs.get("statut", StatutProjetVoyage.EN_PLANIFICATION)
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        return project
    return _create_project


@pytest.fixture
def test_hospital(db):
    """Create a test hospital"""
    hospital = Hospital(
        nom="Test Hospital",
        adresse="123 Test Street",
        ville="Test City",
        pays="Test Country",
        latitude=Decimal("48.8566"),
        longitude=Decimal("2.3522"),
        telephone="+33123456789",
        est_actif=True
    )
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.username,
            "password": "testpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, test_admin):
    """Get authentication headers for admin user"""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_admin.username,
            "password": "adminpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def reception_headers(client, db, test_receptionist, test_hospital):
    test_receptionist.hospital_id = test_hospital.id
    db.commit()
    db.refresh(test_receptionist)
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_receptionist.username,
            "password": "reception123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def hospital_doctor_headers(client, hospital_doctor):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": hospital_doctor.username,
            "password": "docpassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def hospital_referent_headers(client, hospital_referent):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": hospital_referent.username,
            "password": "referent123",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def hospital_accountant_headers(client, hospital_accountant):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": hospital_accountant.username,
            "password": "account123",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def medecin_referent_headers(client, test_doctor):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_doctor.username,
            "password": "doctorpassword123",
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sos_operator_headers(client, test_sos_operator):
    """Get authentication headers for SOS operator"""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_sos_operator.username,
            "password": "sospassword123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

