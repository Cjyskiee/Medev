"""Writes the synthetic demo documents into data/docs/ in the Title/Author/blank/body format."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "docs"

DOCUMENTS = [
    {
        "file": "benign_fibroadenoma_adult.txt",
        "title": "Benign fibroadenoma of the breast in a 29-year-old woman",
        "author": "Dr. A. Reyes",
        "body": (
            "A 29-year-old woman presented with a painless, mobile lump in the left breast that she "
            "had noticed three months earlier. Ultrasound showed a well-circumscribed oval mass with "
            "smooth margins and no acoustic shadowing. Core needle biopsy reported a benign "
            "fibroadenoma with no atypia, no necrosis and no mitotic activity. The lesion was excised "
            "and histology confirmed the diagnosis. Sentinel nodes were not sampled because the "
            "imaging and histology were concordant and benign. At twelve-month follow-up the patient "
            "was well with no recurrence. Source: Synthetic Case Reports in Oncology. Location: "
            "United States. This record is fictional and contains no real patient data."
        ),
    },
    {
        "file": "invasive_ductal_carcinoma_adult.txt",
        "title": "Invasive ductal carcinoma of the breast in a 58-year-old woman",
        "author": "Dr. L. Cruz",
        "body": (
            "A 58-year-old woman was referred after screening mammography showed a 22 mm spiculated "
            "mass with clustered pleomorphic microcalcifications in the right breast. Ultrasound "
            "confirmed an irregular hypoechoic lesion with posterior shadowing. Core biopsy reported "
            "invasive ductal carcinoma, grade 2, oestrogen receptor positive and HER2 negative. "
            "Axillary ultrasound was normal. The patient had breast-conserving surgery with sentinel "
            "node biopsy, and two of three nodes contained metastatic carcinoma. Adjuvant chemotherapy "
            "and radiotherapy were given. Source: Synthetic Case Reports in Oncology. Location: "
            "United States. This record is fictional and contains no real patient data."
        ),
    },
    {
        "file": "benign_phyllodes_adult.txt",
        "title": "Benign phyllodes tumour of the breast in a 44-year-old woman",
        "author": "Dr. M. Santos",
        "body": (
            "A 44-year-old woman reported a rapidly growing, painless mass in the right breast that "
            "had doubled in size over four months. Ultrasound showed a 45 mm well-defined, lobulated, "
            "heterogeneous mass without calcification. Core biopsy suggested a fibroepithelial lesion "
            "with leaf-like architecture and mild stromal cellularity. Wide local excision with a "
            "1 cm margin was performed. Histology confirmed a benign phyllodes tumour with low "
            "mitotic rate, no stromal overgrowth and clear margins. No adjuvant treatment was given. "
            "The patient remained recurrence free at eighteen months. Source: Synthetic Case Reports "
            "in Oncology. Location: Brazil. This record is fictional and contains no real patient data."
        ),
    },
    {
        "file": "pediatric_fibroadenoma.txt",
        "title": "Benign fibroadenoma of the breast in a 15-year-old girl",
        "author": "Dr. P. Nair",
        "body": (
            "A 15-year-old girl was seen with a firm, mobile, non-tender mass in the left breast that "
            "had been present for five months. Ultrasound showed a 20 mm circumscribed oval mass with "
            "smooth margins and homogeneous echotexture. Core biopsy reported a benign fibroadenoma "
            "with no atypia. Because the lesion was benign and the patient was still growing, the "
            "family chose observation rather than excision. The mass was unchanged in size at six and "
            "twelve months. Source: Synthetic Paediatric Case Reports. Location: India. This record is "
            "fictional and contains no real patient data."
        ),
    },
    {
        "file": "pediatric_asthma_cohort.txt",
        "title": "Inhaled corticosteroids in a paediatric asthma cohort",
        "author": "Dr. K. Lindqvist",
        "body": (
            "This prospective cohort enrolled 212 children aged 6 to 11 years with mild to moderate "
            "persistent asthma. All participants started a low-dose inhaled corticosteroid with a "
            "spacer and received a written action plan. Over twelve months the annual rate of severe "
            "exacerbations fell from 0.9 to 0.3 per child, and the mean number of salbutamol rescue "
            "days per month fell from 6.4 to 2.1. Growth velocity was unchanged and no serious adverse "
            "events occurred. Adherence measured by pharmacy refill was 78 percent. The authors "
            "concluded that low-dose inhaled corticosteroids were effective in this paediatric "
            "population. Source: Synthetic Journal of Paediatric Respiratory Medicine. Location: "
            "Sweden. This record is fictional and contains no real patient data."
        ),
    },
    {
        "file": "adult_asthma_trial.txt",
        "title": "Biologic therapy for severe asthma in adults: a randomised trial",
        "author": "Dr. R. Okafor",
        "body": (
            "This double-blind randomised trial assigned 340 adults aged 18 to 65 years with severe "
            "eosinophilic asthma to a monoclonal anti-IL-5 antibody or placebo for 52 weeks. The "
            "annual exacerbation rate was 0.8 in the treatment group and 1.9 in the placebo group. "
            "Pre-bronchodilator FEV1 improved by 210 mL with treatment and by 40 mL with placebo. "
            "Blood eosinophil counts fell by 85 percent in the treatment group. Injection-site "
            "reactions were the most common adverse event and no deaths occurred. The trial concluded "
            "that the biologic reduced exacerbations and improved lung function in adults with severe "
            "eosinophilic asthma. Source: Synthetic Respiratory Trials Journal. Location: "
            "United Kingdom. This record is fictional and contains no real patient data."
        ),
    },
    {
        "file": "type1_diabetes_pediatric.txt",
        "title": "Insulin pump versus injections in children with type 1 diabetes",
        "author": "Dr. S. Almeida",
        "body": (
            "This cohort followed 96 children aged 4 to 14 years with newly diagnosed type 1 diabetes "
            "for two years. Fifty-one used a continuous subcutaneous insulin pump and 45 continued "
            "multiple daily injections. Mean HbA1c at 24 months was 7.2 percent with the pump and 8.0 "
            "percent with injections. Time in range measured by continuous glucose monitoring was 68 "
            "percent versus 55 percent. Severe hypoglycaemia occurred in two pump users and three "
            "injection users. The authors concluded that pump therapy improved glycaemic control in "
            "children with type 1 diabetes without increasing severe hypoglycaemia. Source: Synthetic "
            "Paediatric Diabetes Review. Location: Portugal. This record is fictional and contains no "
            "real patient data."
        ),
    },
    {
        "file": "type2_diabetes_adult.txt",
        "title": "Metformin combined with a GLP-1 agonist in adults with type 2 diabetes",
        "author": "Dr. H. Tanaka",
        "body": (
            "This randomised trial enrolled 540 adults aged 35 to 70 years with type 2 diabetes and "
            "HbA1c between 7.5 and 10.5 percent despite metformin. Participants received a weekly GLP-1 "
            "receptor agonist or placebo for 40 weeks in addition to metformin. HbA1c fell by 1.4 "
            "percentage points with the agonist and by 0.3 with placebo. Mean body weight fell by 4.6 "
            "kg versus 0.8 kg. Gastrointestinal adverse events were reported by 31 percent of the "
            "treatment group and led to discontinuation in 6 percent. No severe hypoglycaemia occurred. "
            "The trial concluded that adding the GLP-1 agonist improved glycaemic control and reduced "
            "weight in adults with type 2 diabetes. Source: Synthetic Metabolic Trials Journal. "
            "Location: Japan. This record is fictional and contains no real patient data."
        ),
    },
    {
        "file": "migraine_review_adult.txt",
        "title": "Triptans for acute migraine in adults: a systematic review",
        "author": "Dr. E. Novak",
        "body": (
            "This systematic review pooled 18 randomised trials of triptans for acute migraine in "
            "adults, with 12,400 participants in total. Pain freedom at two hours was achieved by 32 "
            "percent of participants taking a triptan and 12 percent taking placebo. Freedom from the "
            "most bothersome symptom at two hours was 42 percent versus 17 percent. Triptan use was "
            "associated with more chest tightness and paraesthesia but no increase in serious "
            "cardiovascular events in the trials reviewed. The authors concluded that triptans are "
            "effective for acute migraine in adults and should be offered early in the attack. "
            "Source: Synthetic Headache Evidence Review. Location: Canada. This record is fictional "
            "and contains no real patient data."
        ),
    },
    {
        "file": "prostate_bph_older_adult.txt",
        "title": "Benign prostatic hyperplasia treated with TURP in a 71-year-old man",
        "author": "Dr. J. Whitfield",
        "body": (
            "A 71-year-old man reported nocturia, weak stream and incomplete emptying for two years. "
            "Digital rectal examination showed a smooth, symmetrically enlarged prostate with no "
            "nodules. Prostate-specific antigen was 2.1 ng per mL. Uroflowmetry showed a maximum flow "
            "of 7 mL per second and post-void residual of 120 mL. Transurethral resection of the "
            "prostate was performed. Histology showed benign prostatic hyperplasia with no evidence of "
            "malignancy in 24 grams of tissue. At six months the symptom score had improved from 22 to "
            "6 and the peak flow had risen to 16 mL per second. Source: Synthetic Urology Case "
            "Reports. Location: Australia. This record is fictional and contains no real patient data."
        ),
    },
    {
        "file": "prostate_adenocarcinoma_older_adult.txt",
        "title": "Prostate adenocarcinoma in a 68-year-old man",
        "author": "Dr. J. Whitfield",
        "body": (
            "A 68-year-old man was referred with a prostate-specific antigen of 12.4 ng per mL. "
            "Digital rectal examination revealed a hard nodule in the left lobe. Magnetic resonance "
            "imaging showed a PI-RADS 4 lesion with extracapsular extension. Targeted and systematic "
            "biopsies found adenocarcinoma, Gleason score 4 plus 3, in 6 of 12 cores. Bone scan was "
            "negative. The patient underwent robot-assisted radical prostatectomy with pelvic lymph "
            "node dissection. Histology confirmed adenocarcinoma with negative margins and no nodal "
            "metastasis. Prostate-specific antigen was undetectable at three months. Source: Synthetic "
            "Urology Case Reports. Location: Australia. This record is fictional and contains no real "
            "patient data."
        ),
    },
]


# Writes every document as its own .txt file, replacing files with the same name.
def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for document in DOCUMENTS:
        path = DATA_DIR / document["file"]
        content = (
            f"Title: {document['title']}\n"
            f"Author: {document['author']}\n"
            "\n"
            f"{document['body']}\n"
        )
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.name}")


# Runs the generator when called with "python -m scripts.make_fake_docs".
if __name__ == "__main__":
    main()
