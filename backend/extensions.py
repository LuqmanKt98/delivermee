from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restx import Api

# ORM_DISABLED: SQLAlchemy/Migrate kept as stubs — not active in Firebase mode
db = SQLAlchemy()
migrate = Migrate()

api = Api(
    version="1.0",
    title="DeliverMee API",
    description="RESTful API for the DeliverMee delivery platform",
    doc="/swagger",
    prefix="/api",
    authorizations={
        "Bearer Auth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Firebase ID token — format: Bearer <token>",
        }
    },
    security="Bearer Auth",
)
