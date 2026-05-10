from flask_restx import Namespace, Resource, fields
from extensions import db
from datetime import datetime
import psutil
import os
from settings import USE_FIREBASE_DB
from services.firestore_client import get_firestore

# Initialize namespace
health_api = Namespace('health', description='Health check and system status operations')

# Response models
health_response = health_api.model('HealthResponse', {
    'status': fields.String(description='Overall health status'),
    'timestamp': fields.String(description='Health check timestamp'),
    'database': fields.String(description='Database connection status'),
    'services': fields.Raw(description='Service status information'),
    'system': fields.Raw(description='System resource information'),
    'version': fields.String(description='Application version')
})

@health_api.route('/')
class HealthCheck(Resource):
    @health_api.doc('health_check')
    @health_api.marshal_with(health_response, code=200)
    def get(self):
        """Get overall system health status"""
        try:
            # ORM_DISABLED: PostgreSQL health checks replaced by Firestore checks (date: 2026-02-07)
            # db_status = "healthy"
            # try:
            #     from sqlalchemy import text
            #     db.session.execute(text("SELECT 1"))
            #     db.session.commit()
            # except Exception as e:
            #     db_status = f"unhealthy: {str(e)}"

            db_status = "healthy"
            if USE_FIREBASE_DB:
                try:
                    # minimal Firestore call
                    get_firestore().collection("_health").document("ping").get()
                    db_status = "healthy"
                except Exception as e:
                    db_status = f"unhealthy: {str(e)}"
            else:
                try:
                    from sqlalchemy import text
                    db.session.execute(text("SELECT 1"))
                    db.session.commit()
                except Exception as e:
                    db_status = f"unhealthy: {str(e)}"
            
            # Check system resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Service status
            services_status = {
                "database": db_status,
                "flask": "healthy",
                "jwt": "healthy",
                "migrations": "healthy"
            }
            
            # System info
            system_info = {
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory.percent}%",
                "memory_available": f"{memory.available / (1024**3):.2f} GB",
                "disk_usage": f"{disk.percent}%",
                "disk_free": f"{disk.free / (1024**3):.2f} GB"
            }
            
            health_data = {
                'status': 'healthy' if db_status == "healthy" else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'database': db_status,
                'services': services_status,
                'system': system_info,
                'version': '1.0.0'
            }
            
            return health_data, 200
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }, 500

@health_api.route('/database')
class DatabaseHealth(Resource):
    @health_api.doc('database_health')
    def get(self):
        """Test database connectivity"""
        try:
            # ORM_DISABLED: PostgreSQL-only endpoint replaced by Firestore check (date: 2026-02-07)
            # from sqlalchemy import text
            # result = db.session.execute(text("SELECT version()"))
            # version = result.fetchone()[0]

            if USE_FIREBASE_DB:
                get_firestore().collection("_health").document("ping").get()
                return {
                    "status": "healthy",
                    "database": "Firestore",
                    "timestamp": datetime.utcnow().isoformat(),
                }, 200

            from sqlalchemy import text
            result = db.session.execute(text("SELECT version()"))
            version = result.fetchone()[0]

            return {
                "status": "healthy",
                "database": "PostgreSQL",
                "version": version,
                "timestamp": datetime.utcnow().isoformat(),
            }, 200
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, 500

@health_api.route('/services')
class ServicesHealth(Resource):
    @health_api.doc('services_health')
    def get(self):
        """Check all service statuses"""
        try:
            services = {}
            
            # ORM_DISABLED: PostgreSQL health check replaced by Firestore check (date: 2026-02-07)
            # try:
            #     from sqlalchemy import text
            #     db.session.execute(text("SELECT 1"))
            #     services['database'] = 'healthy'
            # except Exception as e:
            #     services['database'] = f'unhealthy: {str(e)}'
            try:
                if USE_FIREBASE_DB:
                    get_firestore().collection("_health").document("ping").get()
                else:
                    from sqlalchemy import text
                    db.session.execute(text("SELECT 1"))
                services["database"] = "healthy"
            except Exception as e:
                services["database"] = f"unhealthy: {str(e)}"
            
            # Test JWT
            try:
                from extensions import jwt
                services['jwt'] = 'healthy'
            except Exception as e:
                services['jwt'] = f'unhealthy: {str(e)}'
            
            # Test migrations
            try:
                from extensions import migrate
                services['migrations'] = 'healthy'
            except Exception as e:
                services['migrations'] = f'unhealthy: {str(e)}'
            
            # Test pricing service
            try:
                from services.pricing_service import PricingService
                pricing_service = PricingService()
                services['pricing_service'] = 'healthy'
            except Exception as e:
                services['pricing_service'] = f'unhealthy: {str(e)}'
            
            # Test payment service
            try:
                from services.payment_service import PaymentService
                payment_service = PaymentService()
                services['payment_service'] = 'healthy'
            except Exception as e:
                services['payment_service'] = f'unhealthy: {str(e)}'
            
            return {
                'status': 'healthy' if all('healthy' in str(v) for v in services.values()) else 'degraded',
                'services': services,
                'timestamp': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, 500

@health_api.route('/ready')
class ReadinessCheck(Resource):
    @health_api.doc('readiness_check')
    def get(self):
        """Check if the application is ready to serve requests"""
        try:
            # ORM_DISABLED: PostgreSQL readiness check replaced by Firestore check (date: 2026-02-07)
            # from sqlalchemy import text
            # db.session.execute(text("SELECT 1"))
            if USE_FIREBASE_DB:
                get_firestore().collection("_health").document("ping").get()
            else:
                from sqlalchemy import text
                db.session.execute(text("SELECT 1"))
            
            # Check if all required services are available
            from services.pricing_service import PricingService
            from services.payment_service import PaymentService
            from services.notification_service import NotificationService
            
            return {
                'status': 'ready',
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'Application is ready to serve requests'
            }, 200
            
        except Exception as e:
            return {
                'status': 'not_ready',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'Application is not ready to serve requests'
            }, 503
