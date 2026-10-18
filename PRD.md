# PRD: QA Agent

Status: Draft v0.1 (belum disetujui, belum ada kode)

## 1. Ringkasan

QA Agent adalah AI agent (Python + Claude API) yang membuka web app di browser sungguhan, menjelajahinya sendiri, lalu melaporkan bug dengan bukti: langkah reproduksi, screenshot, dan log. Proyek ini dibuat sebagai portofolio AI engineer, jadi kedalaman teknis dan bukti terukur (eval) lebih penting daripada tampilan.

## 2. Tujuan dan non-tujuan

**Tujuan**
- Agent menemukan sebagian besar bug yang sengaja ditanam di app dummy, dengan false positive rendah.
- Hasil eval bisa direproduksi siapa pun yang clone repo ini.
- Bisa dipakai ke URL web app apa pun untuk demo.
- Repo rapi dengan README, demo, dan penjelasan keputusan desain.

**Non-tujuan (v1)**
- Deteksi bug visual/layout dan aksesibilitas.
- Generate test regresi Playwright otomatis (kandidat v2).
- UI web yang rumit. v1 cukup CLI dan laporan HTML.
- Dukungan multi-browser atau multi-user.

## 3. Target pengguna

- **Utama:** recruiter dan hiring manager yang menilai portofolio, serta developer lain yang membaca repo.
- **Sekunder:** web developer (termasuk pembuatnya) yang ingin QA cepat untuk app kecil.

## 4. Ruang lingkup v1

**Jenis bug yang dideteksi**
1. Error teknis: error console JS, request 4xx/5xx, halaman crash.
2. Error fungsional: tombol atau form tidak berfungsi, validasi salah, alur utama macet, hasil tidak sesuai ekspektasi.

**Mode pemakaian**
- Mode eval: jalankan agent ke app dummy, bandingkan dengan ground truth.
- Mode demo: jalankan agent ke URL bebas.

## 5. Kebutuhan fungsional

| ID | Kebutuhan |
|---|---|
| F1 | CLI menerima URL target dan opsi (model, batas langkah, batas biaya). |
| F2 | Agent menjelajah lewat tool: `goto`, `click`, `fill`, `get_page_state`, `report_bug`, `finish`. |
| F3 | Detector pasif mencatat error console, request gagal, dan crash tanpa melibatkan LLM. |
| F4 | `report_bug` mewajibkan judul, langkah reproduksi, perilaku aktual, dan perilaku yang diharapkan. |
| F5 | Screenshot dan log relevan ditempel otomatis oleh kode, bukan diminta dari LLM. |
| F6 | Reporter menghasilkan laporan HTML dan JSON berisi severity, bukti, dan ringkasan run. |
| F7 | App dummy (Flask) punya bug yang bisa dinyalakan/dimatikan per flag, ground truth di `bugs.json`. |
| F8 | Eval harness menjalankan agent ke dummy app, mencocokkan laporan dengan ground truth, dan menghitung recall serta false positive. |

## 6. Desain teknis (ringkas)

**Komponen**
- `browser/`: pembungkus Playwright. Output berupa teks ringkas (teks terlihat dan daftar elemen interaktif), bukan HTML mentah.
- `detectors/`: listener pasif untuk console, network, dan crash.
- `agent/`: loop Claude tool use. Default `claude-sonnet-5-5`, bisa diganti lewat config.
- `report/`: penggabung temuan detector dan agent menjadi laporan.
- `dummy_app/`: Flask dengan login, daftar produk (cari/filter), keranjang, dan checkout.
- `evals/`: harness benchmark.

**Alur:** CLI → agent loop ⇄ browser tools (detector mencatat paralel) → reporter → laporan. Eval harness membungkus alur ini untuk banyak run.

**Keputusan desain utama:** deteksi dibagi dua jalur. Detector pasif untuk bug teknis (murah dan konsisten), LLM untuk bug fungsional (butuh penilaian).

**Agent loop**
- Berhenti saat `finish` dipanggil atau batas langkah tercapai (default 30).
- Konteks dijaga kecil, riwayat lama dipangkas.
- Pengaman: batas langkah, batas biaya per run (hitung token), deteksi aksi berulang 3x.

**Prompt sistem**
- Peran QA engineer yang sistematis: petakan halaman, uji form dengan input valid/kosong/aneh, uji alur utama dari awal sampai akhir.
- Lapor bug hanya dengan bukti konkret. Dilarang menebak.

## 7. App dummy dan ground truth

Target awal 12 bug, masing-masing punya ID dan deskripsi di `bugs.json`.

| Jenis | Contoh |
|---|---|
| Teknis | Error JS saat klik tombol tertentu, `/api/products?page=2` mengembalikan 500, gambar produk 404 |
| Fungsional | Login password salah tetap masuk, total keranjang salah saat qty > 1, filter harga tidak bekerja, checkout menerima email invalid, tombol hapus item tidak menghapus, validasi field kosong tidak muncul |

Eval dijalankan di dua kondisi: app bersih (mengukur false positive) dan app penuh bug (mengukur recall).

## 8. Metrik sukses

| Metrik | Target awal |
|---|---|
| Recall bug tertanam | >= 70% |
| False positive di app bersih | <= 1 per run |
| Biaya per run eval | Terdokumentasi (dicatat tiap run) |
| Reprodusibilitas | Eval dijalankan 1 perintah, hasil berupa tabel |

Angka target adalah tebakan awal dan akan disesuaikan setelah eval pertama.

## 9. Penanganan error

- Tool gagal (selector tidak ada, timeout): error dikembalikan ke agent sebagai teks agar bisa menyesuaikan, tidak membuat run crash.
- Panggilan API gagal: retry dengan backoff, lalu hentikan run dengan laporan parsial.
- Batas langkah atau biaya tercapai: run berhenti dan laporan tetap ditulis dengan status "terpotong".
- API key hilang: CLI berhenti dengan pesan jelas sebelum run dimulai.

## 10. Strategi testing

- Unit test untuk detector, pembungkus browser, dan reporter (tanpa LLM).
- Test integrasi agent loop dengan Claude yang di-mock (respons tool use terskrip).
- Eval end-to-end sebagai benchmark terpisah (memakai API sungguhan, tidak ikut test rutin).

## 11. Struktur folder

```
agent-qa/
  PRD.md
  README.md
  .env / .env.example
  src/agent_qa/
    browser/  detectors/  agent/  report/  cli.py
  dummy_app/   (Flask + bugs.json)
  evals/       (harness + hasil)
  tests/
```

## 12. Risiko

| Risiko | Mitigasi |
|---|---|
| Biaya API membengkak | Batas biaya per run, model bisa diganti, token dicatat |
| Agent berputar-putar | Deteksi aksi berulang, batas langkah |
| False positive tinggi | Aturan lapor berbukti, eval di app bersih |
| Hasil eval tidak stabil antar run | Jalankan beberapa kali, laporkan rata-rata dan rentang |
| Scope melebar | Bug visual, aksesibilitas, dan test regresi ditunda ke v2 |

## 13. Pertanyaan terbuka

- Target recall dan false positive final setelah eval pertama.
- Apakah perlu dukungan login untuk URL bebas (kredensial dari config)?
- Deploy demo publik, atau cukup rekaman GIF di README?

## 14. Rencana bertahap

1. Fondasi: browser tools dan detector pasif, plus test.
2. App dummy dengan bug dan `bugs.json`.
3. Agent loop dan prompt, lalu jalan manual ke dummy app.
4. Reporter dan laporan HTML.
5. Eval harness dan hasil pertama.
6. README, demo, dan polesan.
