from celery import Celery

app = Celery('unihr')
app.config_from_object('app.celery_app')
app.autodiscover_tasks(['app.tasks'])
