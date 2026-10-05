# Corn Disease Flask — Uji Citra Final

Aplikasi deteksi penyakit daun jagung dengan Flask, PWA, upload/kamera, dan pengujian beberapa model klasifikasi.

## Fitur final
- Navbar/sidebar: Dashboard, Processing, Pengujian, Laporan.
- Menu **Pengujian** langsung membuka form **Uji Citra** (upload atau kamera).
- Hanya citra yang lolos validasi daun jagung yang diteruskan ke klasifikasi; gambar non-daun/bukan citra jagung ditolak.
- Kelas penyakit: **Bercak Daun, Hawar Daun, Bulai Daun**.
- Ground truth bersifat **opsional** dan tidak dipakai untuk menentukan kesimpulan prediksi.
- Kesimpulan Uji Citra memilih model dengan **confidence tertinggi** untuk citra yang sedang diuji.
- Light dan Dark mode: **topbar/navbar tetap hijau**.
- Service worker/cache diberi versi baru dan cache lama dibersihkan otomatis oleh `pwa.js`.
- HTTPS/certificate tetap tersedia di folder `certificates/`, tetapi **tidak dijalankan oleh `run.py`**.
- `run.py` menggunakan **HTTP port 5000**.
- ZIP ini **tanpa `.venv`, `venv`, dan `__pycache__`**.

## Menjalankan
1. Buka terminal pada folder project.
2. Buat/aktifkan virtual environment sendiri jika diperlukan.
3. Install dependency:
   `pip install -r requirements.txt`
4. Jalankan:
   `python run.py`
5. Buka:
   `http://127.0.0.1:5000`

## Jika browser masih menyimpan cache lama
Tutup tab aplikasi lalu buka kembali. Versi service worker/cache pada project ini sudah dinaikkan. Jika browser masih memakai worker lama, buka DevTools > Application > Service Workers dan lakukan **Unregister**, lalu reload sekali. DevTools sendiri adalah panel browser dan tidak dapat dihapus oleh Python/Flask.

## HTTPS nanti
File `certificates/corn-disease.pem` dan `certificates/corn-disease-key.pem` tetap disimpan. Untuk sementara `run.py` sengaja tidak menggunakan `ssl_context`.


## Pemisahan Halaman Pengujian
- **Evaluasi Model** (`/comparison` atau `/pengujian`) hanya untuk evaluasi model: Train/Validation/Test, perbandingan C4.5, Gaussian Naive Bayes, KNN, confusion matrix, classification report, dan metrik.
- **Uji Citra** (`/uji-citra`) khusus untuk upload/kamera citra daun jagung dan melihat prediksi, confidence, kemiripan dataset, serta kesimpulan citra.
- Form uji citra tidak lagi berada di halaman Evaluasi Model.
# aplikasi-perbaikan
