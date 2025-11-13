from fastapi import FastAPI
from pydantic import BaseModel
from celery.result import AsyncResult

# Dikkat: worker.py'dan değil, celery_app'ten app'i alıyoruz!
from celery_app import app as celery_app 

# ...ve worker.py'dan "iş tanımını" alıyoruz
from worker import execute_code_task 

# FastAPI uygulamasını başlat
app = FastAPI(
    title="Otomatik Kod Değerlendirme API",
    description="Kodları güvenli bir şekilde çalıştırmak için FastAPI ve Celery kullanan API.",
    version="1.0.0"
)

# --- Veri Modelleri (Pydantic) ---
# API'ye ne tür bir JSON gelmesi gerektiğini tanımlar
class CodeSubmission(BaseModel):
    student_code: str
    input_str: str
    expected_output: str

# API'den ne tür bir JSON döneceğini tanımlar
class JobResponse(BaseModel):
    job_id: str
    status: str

class JobResult(BaseModel):
    job_id: str
    status: str
    result: dict | None = None # Sonuç, eğer hazırsa, bir sözlük (dict) olacak


# --- API Endpoint'leri (Web Adresleri) ---

@app.get("/")
def read_root():
    return {"message": "Kod Değerlendirme API'sine hoş geldiniz!"}

@app.post("/submit", response_model=JobResponse)
def submit_code(submission: CodeSubmission):
    """
    Yeni bir kod çalıştırma işi gönderir.
    Bu endpoint, işi kuyruğa atar ve ANINDA cevap döner.
    """
    print(f"Yeni istek alındı: {submission.student_code[:20]}...")

    # İşi kuyruğa atıyoruz (.delay() ile)
    job = execute_code_task.delay(
        submission.student_code, 
        submission.input_str, 
        submission.expected_output
    )

    # Kullanıcıya "işin alındı, takip numaran (job_id) bu" diyoruz.
    return {"job_id": job.id, "status": "PENDING"}

@app.get("/results/{job_id}", response_model=JobResult)
def get_job_result(job_id: str):
    """
    Gönderilen bir işin durumunu ve sonucunu sorgular.
    """
    # Celery'ye "bu ID'li iş ne durumda?" diye soruyoruz
    job = AsyncResult(job_id, app=celery_app)

    if not job.ready():
        # İş henüz bitmemiş
        return {"job_id": job_id, "status": job.state, "result": None}

    # İş bitmiş, sonucu al
    result = job.get()
    return {"job_id": job_id, "status": job.state, "result": result}