from repository.base_repository import BaseRepository
from sqlalchemy import Table, Column, String, Boolean, MetaData, select, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from passlib.context import CryptContext
import uuid

metadata = MetaData()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ======================
# Table Definitions
# ======================

organizations_table = Table(
    "organizations", metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String, nullable=False),
    Column("domain", String),
    Column("settings", JSONB),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)

users_table = Table(
    "users", metadata,
    Column("id", UUID, primary_key=True),
    Column("organization_id", UUID, nullable=False),
    Column("email", String, nullable=False),
    Column("password_hash", String),
    Column("first_name", String),
    Column("last_name", String),
    Column("role", String, nullable=False),
    Column("is_active", Boolean, default=True),
    Column("profile_data", JSONB),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)

job_positions_table = Table(
    "job_positions", metadata,
    Column("id", UUID, primary_key=True),
    Column("organization_id", UUID, nullable=False),
    Column("title", String, nullable=False),
    Column("description", Text),
    Column("required_skills", JSONB),
    Column("department", String),
    Column("is_active", Boolean, default=True),
    Column("created_by", UUID),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)

interview_templates_table = Table(
    "interview_templates", metadata,
    Column("id", UUID, primary_key=True),
    Column("organization_id", UUID, nullable=False),
    Column("name", String, nullable=False),
    Column("type", String),
    Column("questions", JSONB),
    Column("settings", JSONB),
    Column("created_by", UUID),
    Column("created_at", TIMESTAMP(timezone=True)),
    Column("updated_at", TIMESTAMP(timezone=True)),
)


class UserRepository(BaseRepository):

    # ======================
    # Organization Methods
    # ======================

    def create_organization(self, name: str, domain: str = None, settings: dict = None, has_coding_access: bool = False) -> dict:
        """Create a new organization"""
        org_id = uuid.uuid4()
        
        # Store has_coding_access in settings
        org_settings = settings or {}
        org_settings["has_coding_access"] = has_coding_access
        
        insert_stmt = organizations_table.insert().values(
            id=org_id,
            name=name,
            domain=domain,
            settings=org_settings
        )
        self.session.execute(insert_stmt)
        return {"id": str(org_id), "name": name, "domain": domain, "has_coding_access": has_coding_access}

    def get_organization_by_id(self, org_id: str) -> dict:
        """Get organization by ID"""
        query = select(organizations_table).where(
            organizations_table.c.id == uuid.UUID(org_id)
        )
        result = self.session.execute(query).fetchone()
        if result:
            row = dict(result._mapping)
            row["id"] = str(row["id"])
            
            # Extract has_coding_access from settings
            settings = row.get("settings") or {}
            row["has_coding_access"] = settings.get("has_coding_access", False)
            
            return row
        return None

    def get_organization_by_domain(self, domain: str) -> dict:
        """Get organization by domain"""
        query = select(organizations_table).where(
            organizations_table.c.domain == domain
        )
        result = self.session.execute(query).fetchone()
        if result:
            row = dict(result._mapping)
            row["id"] = str(row["id"])
            
            # Extract has_coding_access from settings
            settings = row.get("settings") or {}
            row["has_coding_access"] = settings.get("has_coding_access", False)
            
            return row
        return None

    def update_organization(self, org_id: str, **kwargs) -> dict:
        """Update an organization"""
        
        # Handle settings update properly especially for has_coding_access
        clean_kwargs = kwargs.copy()
        
        # If we need to update has_coding_access, we must read-modify-write settings
        if "has_coding_access" in clean_kwargs:
            new_access_value = clean_kwargs.pop("has_coding_access")
            
            # Get current settings
            current_org = self.get_organization_by_id(org_id)
            if not current_org:
                return None
                
            settings = current_org.get("settings") or {}
            settings["has_coding_access"] = new_access_value
            clean_kwargs["settings"] = settings
            
        update_stmt = organizations_table.update().where(
            organizations_table.c.id == uuid.UUID(org_id)
        ).values(**clean_kwargs)
        
        self.session.execute(update_stmt)
        return self.get_organization_by_id(org_id)

    # ======================
    # User Methods
    # ======================

    def create_user(self, organization_id: str, email: str, password: str,
                    first_name: str, last_name: str, role: str = "recruiter") -> dict:
        """Create a new user with hashed password"""
        user_id = uuid.uuid4()
        insert_stmt = users_table.insert().values(
            id=user_id,
            organization_id=uuid.UUID(organization_id),
            email=email,
            password_hash=pwd_context.hash(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True
        )
        self.session.execute(insert_stmt)
        return {
            "id": str(user_id),
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "organization_id": organization_id
        }

    def get_user_by_email(self, email: str) -> dict:
        """Get user by email"""
        query = select(users_table).where(users_table.c.email == email)
        result = self.session.execute(query).fetchone()
        if result:
            row = dict(result._mapping)
            row["id"] = str(row["id"])
            row["organization_id"] = str(row["organization_id"])
            return row
        return None

    def get_user_by_id(self, user_id: str) -> dict:
        """Get user by ID"""
        query = select(users_table).where(users_table.c.id == uuid.UUID(user_id))
        result = self.session.execute(query).fetchone()
        if result:
            row = dict(result._mapping)
            row["id"] = str(row["id"])
            row["organization_id"] = str(row["organization_id"])
            return row
        return None

    def get_all_users(self):
        """Get all users"""
        query = select(users_table)
        result = self.session.execute(query)
        users = []
        for row in result.mappings().all():
            user = dict(row)
            user["id"] = str(user["id"])
            user["organization_id"] = str(user["organization_id"])
            users.append(user)
        return users

    def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        query = select(users_table).where(users_table.c.email == email)
        result = self.session.execute(query).fetchone()
        return result is not None

    # ======================
    # Job Position Methods
    # ======================

    def create_job_position(self, organization_id: str, title: str, description: str = None,
                            required_skills: list = None, department: str = None,
                            created_by: str = None) -> dict:
        """Create a new job position"""
        job_id = uuid.uuid4()
        insert_stmt = job_positions_table.insert().values(
            id=job_id,
            organization_id=uuid.UUID(organization_id),
            title=title,
            description=description,
            required_skills=required_skills or [],
            department=department,
            is_active=True,
            created_by=uuid.UUID(created_by) if created_by else None
        )
        self.session.execute(insert_stmt)
        return {
            "id": str(job_id),
            "organization_id": organization_id,
            "title": title,
            "description": description,
            "required_skills": required_skills or [],
            "department": department,
            "is_active": True
        }

    def get_job_positions_by_org(self, organization_id: str, active_only: bool = True) -> list:
        """Get all job positions for an organization"""
        query = select(job_positions_table).where(
            job_positions_table.c.organization_id == uuid.UUID(organization_id)
        )
        if active_only:
            query = query.where(job_positions_table.c.is_active == True)

        query = query.order_by(job_positions_table.c.created_at.desc())
        result = self.session.execute(query)

        jobs = []
        for row in result.mappings().all():
            job = dict(row)
            job["id"] = str(job["id"])
            job["organization_id"] = str(job["organization_id"])
            if job.get("created_by"):
                job["created_by"] = str(job["created_by"])
            jobs.append(job)
        return jobs

    def get_job_position_by_id(self, job_id: str) -> dict:
        """Get job position by ID"""
        query = select(job_positions_table).where(
            job_positions_table.c.id == uuid.UUID(job_id)
        )
        result = self.session.execute(query).fetchone()
        if result:
            job = dict(result._mapping)
            job["id"] = str(job["id"])
            job["organization_id"] = str(job["organization_id"])
            if job.get("created_by"):
                job["created_by"] = str(job["created_by"])
            return job
        return None

    def update_job_position(self, job_id: str, **kwargs) -> dict:
        """Update a job position"""
        update_stmt = job_positions_table.update().where(
            job_positions_table.c.id == uuid.UUID(job_id)
        ).values(**kwargs)
        self.session.execute(update_stmt)
        return self.get_job_position_by_id(job_id)

    def delete_job_position(self, job_id: str) -> bool:
        """Soft delete a job position (set is_active=False)"""
        update_stmt = job_positions_table.update().where(
            job_positions_table.c.id == uuid.UUID(job_id)
        ).values(is_active=False)
        self.session.execute(update_stmt)
        return True

    # ======================
    # Interview Template Methods
    # ======================

    def create_interview_template(self, organization_id: str, name: str,
                                   template_type: str = None, questions: list = None,
                                   settings: dict = None, created_by: str = None) -> dict:
        """Create a new interview template"""
        template_id = uuid.uuid4()
        insert_stmt = interview_templates_table.insert().values(
            id=template_id,
            organization_id=uuid.UUID(organization_id),
            name=name,
            type=template_type,
            questions=questions,
            settings=settings or {},
            created_by=uuid.UUID(created_by) if created_by else None
        )
        self.session.execute(insert_stmt)
        return {
            "id": str(template_id),
            "organization_id": organization_id,
            "name": name,
            "type": template_type,
            "questions": questions,
            "settings": settings or {}
        }
