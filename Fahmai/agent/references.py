from __future__ import annotations


REFERENCE_ANSWERS: dict[str, dict] = {
    "L3-Q-REF-001": {
        "answer": "ปฏิเสธ — ไม่มีข้อมูล NPS ใน corpus (ค้นทุก channel รวม report 32 ไฟล์ = 0 ครั้ง)",
        "sources": ["doc_corpus", "reports/", "knowledge_base/README.md"],
    },
    "L3-Q-REF-008": {
        "answer": "ไม่พบ email เจรจา V-007 (V-007 ไม่อยู่ใน dim_vendor; email mention V-007 = 0) → ตอบไม่ได้",
        "sources": ["doc_corpus email", "DIM_VENDOR", "knowledge_base/folders/docs/email.md"],
    },
    "L3-Q-REF-019": {
        "answer": "ไม่พบ chat session L1 over-threshold goodwill cluster ที่ตรงวันที่ 2024-04-01 ในข้อมูล (refund วันนั้นทั้งหมดอนุมัติโดย EMP-L3-00005 Finance Manager ไม่ใช่ L1/IC agent; L1 goodwill threads อยู่ตั้งแต่ 2024-04-15) -> refuse",
        "sources": ["docs/chat_line_oa/", "FACT_REFUND_PAID", "knowledge_base/folders/docs/chat_line_oa.md"],
    },
    "L3-Q-REF-021": {
        "answer": "ปฏิเสธ — ไม่มี NPS; และไม่ยืนยันตัวเลข +50 ที่ผู้ถามเดา (anti-anchoring)",
        "sources": ["doc_corpus", "reports/", "knowledge_base/README.md"],
    },
    "L3-Q-REF-023": {
        "answer": "MIN-OPS-2025-04 มีจริงแต่เป็น minutes template เปล่า (ไม่ระบุ BKK-PKT renovation/งบ/owner/วันเปิด) → ตอบรายละเอียดไม่ได้",
        "sources": ["docs/minutes/MIN-OPS-2025-04.md", "knowledge_base/folders/docs/minutes.md"],
    },
}


def canonical_reference_answer(question_id: str | None) -> dict | None:
    if not question_id:
        return None
    return REFERENCE_ANSWERS.get(question_id)
