from celery_app import app  # 1. Adım'daki "Kuyruk Yöneticisi"ni içe aktar
from sprint1_motor import run_python_code  # Sprint 1'deki "Motor"umuzu içe aktar
import time

# 'app.task' decorator'ı, bu fonksiyonun bir "iş" olduğunu Celery'ye bildirir.
@app.task(name='tasks.execute_code_task')
def execute_code_task(student_code, input_str, expected_output):
    """
    Celery tarafından tetiklenecek olan asıl iş.
    Bu fonksiyon, Sprint 1 motorunu çalıştırır.
    """
    print(f"İş alındı: {student_code[:20]}...")

    # Sprint 1 motorumuzu çağırıyoruz
    result = run_python_code(
        student_code_str=student_code,
        input_str=input_str,
        expected_output_str=expected_output
    )

    print(f"İş tamamlandı: {result['status']}")

    # Fonksiyondan bir değer 'return' ettiğimizde,
    # Celery bu sonucu otomatik olarak 'backend'e (Redis'e) kaydeder.
    return result

print("İşçi (Worker) tanımlamaları yüklendi.")