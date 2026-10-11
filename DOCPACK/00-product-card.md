---
title: polyglot-benchmark-lab — Product Card
doc_id: CARD-polyglot-benchmark-lab
doc_type: product-card
verdict: showcase
version: 0.1
date: 2026-10-11
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
---

# polyglot-benchmark-lab — Product Card

## 1. สรุปคุณค่าในหนึ่งประโยค

ช่วยนักพัฒนาที่เลือกภาษา/เฟรมเวิร์กฝั่ง backend เปรียบเทียบประสิทธิภาพ Python, TypeScript, Go และ Rust ด้วย workload เดียวกันพร้อมบันทึกการรันที่ตรวจย้อนได้

## 2. ปัญหาและผู้ใช้เป้าหมาย

- ปัญหา: ตัวเลข benchmark ทั่วไปเทียบกันไม่ได้เพราะ workload และสภาพแวดล้อมต่างกัน
- ผู้ใช้เป้าหมาย: นักพัฒนา/สถาปนิกที่เลือกเฟรมเวิร์ก — ผู้ใช้จริง **[ต้องยืนยัน]**

## 3. สิ่งที่ทำได้จริงตอนนี้

- README ระบุ lane หลัก 4 แบบ (`python-fastapi`, `typescript-fastify`, `go-nethttp`, `rust-axum`) และ variant lane 13 แบบ ที่เปลี่ยนทีละจุดเทียบ parent บน VM เดียวกัน
- 5 workload: `W1-json`, `W2-hash`, `W3-http-read`, `W4-http-db`, `W5-cold-start`; ทุก lane ต้องผ่าน contract test (`contract/`, `tests/test_contract.py`) ก่อนวัด
- ผลลัพธ์อยู่ใน `results/` (record ต่อการรัน: commit, runner, runtime, settings) และหน้าเว็บ `site/`; README บันทึกข้อค้นพบเรื่อง Nagle/delayed ACK กับ uvicorn หลาย worker

## 4. หลักฐานสถานะ

| รายการ | ค่า (ตรวจจาก repository) |
|---|---|
| Stack | Python, TypeScript, Go, Rust (ตาม README) |
| Commits | 16 (แรก 2026-10-11 → ล่าสุด 2026-10-11) |
| Source | 528 ไฟล์ (ตัวเลขบรรทัดจาก repo_facts รวมผลลัพธ์/เว็บ จึงไม่ใช้) |
| Tests | 1 ไฟล์ |
| CI | 2 workflow |
| Deploy config | GitHub Actions `ci.yml` และ `bench.yml`; หน้าผลลัพธ์ Vercel https://polyglot-benchmark-lab.vercel.app (ตาม README ไม่ได้ตรวจสถานะ) |
| Live URL | https://polyglot-benchmark-lab.vercel.app |
| README | 106 บรรทัด |

## 5. คุณค่าและจุดต่าง

- จุดต่าง: ทุกตัวเลขเก็บ run record และ lane ต้องผ่าน contract เดียวกัน ไม่ใช่ตัวเลขลอย
- มุมรายได้: ไม่มีโดยตรง — เป็นหลักฐานความเชี่ยวชาญ/เนื้อหาเทคนิค **[สมมติฐาน]**

## 6. ช่องว่างสำคัญ

- สร้างเมื่อ 2026-10-11 (repo เพิ่งสร้าง) ผลวัดยังเป็นของ GitHub-hosted runner ซึ่งมีความแปรปรวนสูง
- ไม่มีเทสต์นอกจาก contract test 1 ไฟล์
- ผู้ใช้/ผู้อ่านจริงยังไม่ยืนยัน

## 7. คำตัดสิน

**`showcase`** — หลักฐานงานวิศวกรรมที่เป็นระบบและโปร่งใส แต่ไม่ใช่ธุรกิจ; จะเปลี่ยนเป็น `invest` ถ้าเป็นแหล่งเนื้อหาที่ดึงผู้อ่านหรือลูกค้าที่ปรึกษาได้

## 8. ขั้นต่อไป

1. ยืนยันสถานะ CI และหน้า Vercel
2. เผยแพร่ผลสรุปพร้อมข้อจำกัดของ runner และวัดผู้อ่าน

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `runner/`, `workloads/`, `contract/`, `results/`, `.github/workflows/`
