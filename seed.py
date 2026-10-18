import asyncio
from app.core.database import AsyncSessionLocal
from app.crud.company import crud_company
from app.crud.user import crud_user
from app.crud.driver import crud_driver
from app.crud.client import crud_client
from app.crud.assignment import crud_assignment
from app.schemas.company import CompanyCreate
from app.schemas.user import UserCreate
from app.schemas.driver import DriverCreate
from app.schemas.client import ClientCreate
from app.schemas.assignment import AssignmentCreate
from app.models.enums import UserRole, DayOfWeek, Shift


async def seed():
    print("Seeding initial development data...")
    async with AsyncSessionLocal() as db:
        # 1. Create Company
        existing_company = await crud_company.get_by_cnpj(db, "12.345.678/0001-99")
        if not existing_company:
            company = await crud_company.create(
                db,
                CompanyCreate(
                    name="Transportes Universitários LongBeach",
                    cnpj="12.345.678/0001-99",
                    phone="(11) 99999-8888",
                    is_active=True,
                ),
            )
            print(f"Company created: {company.name} (ID: {company.id})")
        else:
            company = existing_company
            print(f"Company already exists: {company.name}")

        # 2. Create Admin User
        admin_user = await crud_user.get_by_email(db, "admin@longbeach.com")
        if not admin_user:
            admin_user = await crud_user.create(
                db,
                UserCreate(
                    email="admin@longbeach.com",
                    password="admin123",
                    full_name="Administrador do Sistema",
                    phone="(11) 98888-0000",
                    role=UserRole.ADMIN,
                    is_active=True,
                ),
            )
            print("Admin created: admin@longbeach.com / admin123")

        # 3. Create Driver User & Profile
        driver_user = await crud_user.get_by_email(db, "motorista@longbeach.com")
        if not driver_user:
            driver_user = await crud_user.create(
                db,
                UserCreate(
                    email="motorista@longbeach.com",
                    password="driver123",
                    full_name="Carlos Motorista",
                    phone="(11) 97777-1111",
                    role=UserRole.DRIVER,
                    is_active=True,
                ),
            )
            driver = await crud_driver.create(
                db,
                DriverCreate(
                    user_id=driver_user.id,
                    company_id=company.id,
                    cnh="12345678900",
                    vehicle_model="Mercedes Sprinter 2023",
                    vehicle_plate="ABC-1D23",
                    vehicle_capacity=18,
                    is_available=True,
                ),
            )
            print("Driver created: motorista@longbeach.com / driver123")
        else:
            driver = await crud_driver.get_by_user_id(db, driver_user.id)

        # 4. Create Client User & Profile
        client_user = await crud_user.get_by_email(db, "cliente@longbeach.com")
        if not client_user:
            client_user = await crud_user.create(
                db,
                UserCreate(
                    email="cliente@longbeach.com",
                    password="client123",
                    full_name="Maria Estudante",
                    phone="(11) 96666-2222",
                    role=UserRole.CLIENT,
                    is_active=True,
                ),
            )
            client = await crud_client.create(
                db,
                ClientCreate(
                    user_id=client_user.id,
                    company_id=company.id,
                    pickup_address="Av. Paulista, 1000 - Bela Vista, São Paulo - SP",
                    pickup_latitude=-23.5651,
                    pickup_longitude=-46.6517,
                    destination_address="Rua da Universidade, 500 - Butantã, São Paulo - SP",
                    destination_latitude=-23.5580,
                    destination_longitude=-46.7315,
                    notes="Esperar na portaria principal",
                    is_active=True,
                ),
            )
            print("Client created: cliente@longbeach.com / client123")
        else:
            client = await crud_client.get_by_user_id(db, client_user.id)

        # 5. Create Driver-Client Assignment
        if driver and client:
            assignments = await crud_assignment.get_multi(
                db,
                company_id=company.id,
                driver_id=driver.id,
                client_id=client.id,
            )
            if not assignments:
                assignment = await crud_assignment.create(
                    db,
                    AssignmentCreate(
                        company_id=company.id,
                        driver_id=driver.id,
                        client_id=client.id,
                        day_of_week=DayOfWeek.ALL,
                        shift=Shift.MORNING,
                        pickup_order=1,
                        estimated_pickup_time="06:45",
                        is_active=True,
                    ),
                )
                print(f"Assignment linked: Driver '{driver_user.full_name}' -> Client '{client_user.full_name}' (Morning)")

    print("Seed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
