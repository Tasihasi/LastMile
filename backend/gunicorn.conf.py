"""Gunicorn configuration.

Auto-loaded by gunicorn because the Render start command runs from the
`backend/` directory (`cd backend && gunicorn config.wsgi`), and gunicorn
picks up a `gunicorn.conf.py` in its working directory.

Only timeout-related settings are defined here on purpose: bind address,
port and worker count stay under the control of the Render start command /
defaults so this file can't break the existing deployment.

Why the long timeout: the geocoding endpoint streams results one stop per
second (Nominatim's rate limit). With gunicorn's 30s default, a worker
handling a route of more than ~30 stops is killed mid-stream, so only the
first ~30 addresses get geocoded. Raising the timeout lets a single pass
cover a large route; the frontend additionally resumes geocoding in passes
until no stops remain, so arbitrarily large routes complete either way.
"""

# Seconds a worker may run a request before being killed. 0 would disable the
# timeout entirely, but that lets a genuinely hung worker live forever; 600s is
# generous enough for very large routes while still recycling stuck workers.
timeout = 600

# Give in-flight streamed responses time to flush on restart/reload.
graceful_timeout = 60

# Recycle workers periodically to bound memory growth on long-lived processes.
max_requests = 1000
max_requests_jitter = 100
