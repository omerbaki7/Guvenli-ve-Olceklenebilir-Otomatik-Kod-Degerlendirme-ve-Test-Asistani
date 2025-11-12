import docker
import tarfile
import io
import time
import textwrap

# Docker SDK istemcisini başlat
client = docker.from_env()

def run_python_code(student_code_str, input_str, expected_output_str, timeout_sec=10, mem_limit="256m"):
    """
    Bir Python kodunu Docker container içinde güvenle çalıştırır,
    girdi sağlar, çıktıyı alır ve beklenen çıktı ile karşılaştırır.
    """
    container = None
    
    # 1. Hafızada (in-memory) bir tar arşivi oluştur
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        # Öğrenci kodunu main.py olarak ekle
        code_bytes = student_code_str.encode('utf-8')
        code_info = tarfile.TarInfo(name='main.py')
        code_info.size = len(code_bytes)
        code_info.mtime = time.time()
        tar.addfile(code_info, io.BytesIO(code_bytes))
        
        # Input'u input.txt olarak ekle
        input_bytes = input_str.encode('utf-8')
        input_info = tarfile.TarInfo(name='input.txt')
        input_info.size = len(input_bytes)
        input_info.mtime = time.time()
        tar.addfile(input_info, io.BytesIO(input_bytes))
        
    tar_stream.seek(0) # Stream'i başa al

    try:
        # 2. Güvenlik kısıtlamalarıyla Docker container'ını başlat
        #    'python:3.10-slim' imajının yerelde bulunduğundan emin ol
        #    (docker pull python:3.10-slim)
        container = client.containers.run(
            image='python:3.10-slim',
            command="sleep 60", # Dosya kopyalama işlemi için canlı tut
            detach=True,
            mem_limit=mem_limit,
            network_disabled=True, # AĞ ERİŞİMİ KAPALI
            nano_cpus=1000000000 # 1 CPU çekirdeği
        )
        
        # 3. Hazırlanan tar arşivini container içine kopyala
        container.put_archive(path='/app', data=tar_stream)

        # 4. Kodu container içinde çalıştır (exec_run)
        #    Linux 'timeout' komutunu kullanarak zaman aşımını yönet
        command_to_run = f"timeout {timeout_sec} python /app/main.py < /app/input.txt"
        
        # Komutu shell içinde çalıştır (/bin/sh -c ...)
        exec_result = container.exec_run(cmd=["/bin/sh", "-c", command_to_run], demux=True)

        exit_code = exec_result.exit_code
        stdout_bytes = exec_result.output[0] if exec_result.output[0] else b''
        stderr_bytes = exec_result.output[1] if exec_result.output[1] else b''

        # 5. Sonuçları Değerlendir
        if stderr_bytes:
            return {"status": "Çalışma Zamanı Hatası", "output": stderr_bytes.decode('utf-8')}
            
        if exit_code == 124: # 'timeout' komutunun çıkış kodu
            return {"status": "Zaman Aşımı (Timeout)", "output": ""}

        if exit_code != 0:
            return {"status": f"Bilinmeyen Hata (Exit Code: {exit_code})", "output": ""}

        # Çıktıdaki satır sonu karakterlerini normalleştir (Windows/Linux farkı)
        actual_output = stdout_bytes.decode('utf-8').strip().replace('\r\n', '\n')
        expected_output_clean = expected_output_str.strip().replace('\r\n', '\n')

        if actual_output == expected_output_clean:
            return {"status": "Başarılı", "output": actual_output}
        else:
            return {"status": "Yanlış Cevap", "output": actual_output, "expected": expected_output_clean}

    except docker.errors.ImageNotFound:
        return {"status": "Hata", "output": "Docker imajı bulunamadı (python:3.10-slim)."}
    except Exception as e:
        return {"status": "Sistem Hatası", "output": str(e)}
    finally:
        # 6. Temizlik: Ne olursa olsun container'ı durdur ve sil
        if container:
            try:
                container.stop()
                container.remove()
                # print("Container temizlendi.")
            except docker.errors.NotFound:
                pass # Zaten silinmiş/bulunamıyorsa sorun yok
            except Exception as e:
                print(f"Container temizlenirken hata oluştu: {e}")

# --- BU KODU TEST ETMEK İÇİN ---

# Senaryo 1: Başarılı Kod
print("--- Test 1: Başarılı Senaryo ---")
basarili_kod = """
# Kullanıcıdan bir sayı al ve iki katını yazdır
try:
    line = input()
    num = int(line)
    print(f"Sonuç: {num * 2}")
except EOFError:
    pass
"""
girdi_1 = "10"
beklenen_cikti_1 = "Sonuç: 20"
print(run_python_code(basarili_kod, girdi_1, beklenen_cikti_1))
print("-" * 30)


# Senaryo 2: Yanlış Cevap
print("--- Test 2: Yanlış Cevap Senaryosu ---")
yanlis_kod = """
# Hatalı mantık, 2 katı yerine 3 katını alıyor
try:
    line = input()
    num = int(line)
    print(f"Sonuç: {num * 3}")
except EOFError:
    pass
"""
print(run_python_code(yanlis_kod, girdi_1, beklenen_cikti_1))
print("-" * 30)


# Senaryo 3: Sonsuz Döngü (Zaman Aşımı)
print("--- Test 3: Zaman Aşımı Senaryosu ---")
timeout_kod = """
# Sonsuz döngü
while True:
    pass
"""
print(run_python_code(timeout_kod, girdi_1, beklenen_cikti_1, timeout_sec=3)) # 3 saniye limit
print("-" * 30)


# Senaryo 4: Hatalı Kod (Çalışma Zamanı Hatası)
print("--- Test 4: Çalışma Zamanı Hatası ---")
hatali_kod = """
# Sıfıra bölme hatası
x = 10 / 0
print(x)
"""
print(run_python_code(hatali_kod, girdi_1, beklenen_cikti_1))
print("-" * 30)