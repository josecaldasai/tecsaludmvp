"""Gunicorn configuration for TecSalud Chatbot Document Processing API."""

import multiprocessing
import os
from app.settings.v1.settings import SETTINGS

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Restart workers after this many requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Timeout settings
timeout = 120
keepalive = 5
graceful_timeout = 30

# Application
wsgi_app = "main:app"

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = SETTINGS.GENERAL.LOG_LEVEL.lower()
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
)

# Process naming
proc_name = "tecsalud-chatbot-api"

# Daemon mode
daemon = False

# PID file
pidfile = "/tmp/tecsalud-chatbot-api.pid"

# User and group
user = os.getenv("API_USER", "nobody")
group = os.getenv("API_GROUP", "nobody")

# Directories
tmp_upload_dir = "/tmp"

# SSL (if needed)
keyfile = os.getenv("SSL_KEYFILE")
certfile = os.getenv("SSL_CERTFILE")

# Worker limits
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8192

# Preload application
preload_app = True

# Enable SSL redirect (if SSL is configured)
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Enable forwarded headers
forwarded_allow_ips = "*"

# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting TecSalud Chatbot Document Processing API")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading TecSalud Chatbot Document Processing API")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("TecSalud Chatbot Document Processing API is ready")

def worker_int(worker):
    """Called just after a worker has been killed by a signal."""
    worker.log.info("Worker killed by signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Worker {worker.pid} forked")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info(f"Worker {worker.pid} initialized")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"Worker {worker.pid} aborted")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process")

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug(f"Processing request: {req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    worker.log.debug(f"Completed request: {req.method} {req.path} - {resp.status_code}")

def child_exit(server, worker):
    """Called just after a worker has been reaped."""
    server.log.info(f"Worker {worker.pid} exited")

def worker_exit(server, worker):
    """Called just after a worker has been reaped."""
    server.log.info(f"Worker {worker.pid} terminated")

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    server.log.info(f"Number of workers changed from {old_value} to {new_value}")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("Shutting down TecSalud Chatbot Document Processing API")

# Environment variables
raw_env = [
    f'PYTHONPATH={os.getenv("PYTHONPATH", "")}',
    f'TZ={os.getenv("TZ", "UTC")}',
]

# Memory and resource limits
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance
worker_memory_limit = 512 * 1024 * 1024  # 512MB per worker

# Enable automatic worker restarts on memory usage
max_memory_per_child = 512 * 1024 * 1024  # 512MB

# Enable stats collection
statsd_host = os.getenv("STATSD_HOST")
statsd_prefix = "tecsalud.chatbot.api"

# Enable Prometheus metrics (if prometheus_client is installed)
prometheus_multiproc_dir = os.getenv("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc_dir")

# Custom configuration based on environment
if SETTINGS.GENERAL.PRODUCTION:
    # Production settings
    workers = multiprocessing.cpu_count() * 2 + 1
    worker_class = "uvicorn.workers.UvicornWorker"
    timeout = 120
    keepalive = 5
    max_requests = 1000
    max_requests_jitter = 100
    preload_app = True
    
    # Enable access logging in production
    accesslog = "/var/log/tecsalud-chatbot-api/access.log"
    errorlog = "/var/log/tecsalud-chatbot-api/error.log"
    
else:
    # Development settings
    workers = 1
    worker_class = "uvicorn.workers.UvicornWorker"
    timeout = 300
    keepalive = 2
    max_requests = 100
    max_requests_jitter = 10
    preload_app = False
    reload = True
    
    # Use console logging in development
    accesslog = "-"
    errorlog = "-" 