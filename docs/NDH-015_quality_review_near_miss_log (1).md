---
doc_id: NDH-015
doc_type: quality_review
organ_system: multi
diagnosis: Near-miss log: look-alike cases treated or searched as the same condition
category: quality_review_misclassification
confirmed_by: Multidisciplinary Quality Committee (synthetic)
look_alike_docs: [NDH-001, NDH-002, NDH-003, NDH-004, NDH-005, NDH-006, NDH-007, NDH-008, NDH-010, NDH-011, NDH-012, NDH-013]
confusion_risk: reference
---
# Quality Review NDH-015: Near-Miss Log for Look-Alike Cases
Northgate Demo Hospital | Quality Committee | 2026-02-10 | SYNTHETIC DEMO DATA, not real events

## Purpose
Records five near-miss events where a case was nearly handled as a different, similar-looking condition. Each entry links to the correct case file.

## Event 1: Lung nodule, wrong "cancer" assumption
Referral letter for PT-47720 read "spiculated PET-avid nodule in smoker, suspected lung cancer, book lobectomy". Pathology review (NDH-003) showed fungal granuloma. Surgery cancelled before incision. Contrast with true cancer in NDH-002 and a benign hamartoma in NDH-001.

## Event 2: Breast mass, wrong "benign" assumption
PT-40688 was reassured as fibroadenoma from a core biopsy reading "favor fibroadenoma". The mass later reached 7.2 cm. Final diagnosis: borderline phyllodes tumor (NDH-005). Surveillance plan of NDH-004 was NOT appropriate.

## Event 3: Smooth breast cancer under-called
A circumscribed hypoechoic mass in PT-44102 was initially scored low-suspicion. Biopsy confirmed triple-negative carcinoma (NDH-006). Lesson: smooth margins do not exclude malignancy.

## Event 4: Thyroid overtreatment
A pathology report for PT-36240 containing "papillary-like nuclear features" was summarized in a handoff note as "papillary carcinoma". Total thyroidectomy with radioactive iodine was proposed. Review found NIFTP (NDH-007); lobectomy alone was correct. True papillary carcinoma is NDH-008.

## Event 5: Brain lesion, steroids before antibiotics
PT-50276 with a ring-enhancing lesion was triaged as "high-grade glioma" and queued for tumor-protocol steroids. Fever and diffusion pattern prompted aspiration; abscess confirmed (NDH-011). Compare NDH-010.

## Search-system observation (keyword failures)
A plain keyword search for "enhancing liver lesion" returns both NDH-012 (benign hemangioma) and NDH-013 (hepatocellular carcinoma) with near-identical scores. A search for "papillary thyroid" returns both NDH-007 and NDH-008. Results must be grouped by confirmed diagnosis and category, not by wording.
