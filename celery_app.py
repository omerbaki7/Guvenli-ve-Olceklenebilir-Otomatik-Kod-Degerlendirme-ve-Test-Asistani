from celery import Celery

# Redis'in adresini belirtiyoruz.
# 'kod-test-redis' Docker'da verdiğimiz isim, ama biz en kolayıyla localhost diyelim.
REDIS_URL = 'redis://localhost:6379'

# Celery uygulamasını oluştur
# 'broker' -> İş kuyruğunun (emirlerin) tutulduğu yer
# 'backend' -> İş bittikten sonra sonuçların tutulduğu yer
app = Celery(
    'tasks',
    broker=f"{REDIS_URL}/0",  # Kuyruk için Redis DB 0
    backend=f"{REDIS_URL}/1"  # Sonuçlar için Redis DB 1
)

# Celery için bazı ayarlar
app.conf.update(
    task_serializer='json',
    accept_content=['json'],  
    result_serializer='json',
    timezone='Europe/Istanbul',
    enable_utc=True,
)
import worker
# print("Celery uygulaması yapılandırıldı.")