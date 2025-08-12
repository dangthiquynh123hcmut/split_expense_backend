#Split expense Backend

A Django-based backend application for managing group and split expense.

## Setup Instructions

### For development environment

```bash
make install-dev
```

### For production environment

```bash
make install-prod
```

### Setup PostgreSQL Database

1. **Create a PostgreSQL database**:

   - Open your PostgreSQL client and create a new database with command:
     ```sql
     CREATE DATABASE <database_name>;
     ```

2. **Configure the database settings**:
   - Create a `.env` file in the root directory of the project and add the following lines:
     ```env
        POSTGRES_DB=<database_name> # e.g. split_expense_db
        POSTGRES_USER=<postgres_user> # e.g. postgres
        POSTGRES_PASSWORD=<postgres_password> # e.g. postgres
        POSTGRES_HOST=<postgres_host> # e.g. localhost
        POSTGRES_PORT=5432
     ```

### Setup Django Application

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```
2. **Activate the virtual environment**:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   - For development:
     ```bash
     pip install -r requirements-dev.txt
     ```
4. **Run database migrations**:
   ```bash
   cd src
   ```
   ```bash
   python manage.py migrate
   ```
5. **Create a superuser**:
   ```bash
   python manage.py createsuperuser
   ```
6. **Run the server**:
   ```bash
   python manage.py runserver
   ```
7. **Access the application**:
   - Open your web browser and go to `http://localhost:8000/` to access the application.
   - Open your web browser and go to `http://localhost:8000/admin/` to access the Django admin interface.
   - Open your web browser and go to `http://localhost:8000/api/docs` to access the API documentation.

## Service Architecture and Data Flow

```
Controller -> Service -> ORM -> Database
```

- **Controller**: Handles incoming requests and routes them to the appropriate service.
- **Service**: Contains the business logic and interacts with the ORM.
- **ORM**: Maps the service layer to the database, allowing for easy data manipulation.
- **Database**: Stores the application's data. -->
