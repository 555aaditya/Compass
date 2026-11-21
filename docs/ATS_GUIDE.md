# ATS guide

## What the system does
`finalize` compiles the tailored LaTeX, extracts text from the PDF (pdftotext, else pypdf), and checks:
text extracted, standard section headings, contact info (email, phone, GitHub, LinkedIn, near the top), skills readable,
dates and education extractable, replacement/private-use characters, bullet order and content versus the LaTeX source
(catches a PDF that looks right but extracts wrongly), link annotations present and well formed, layout risks in the
source (multi-column, images, text boxes, headers/footers, white text), and page count.

## Keyword coverage
Each requirement from the job is classed required/preferred/mentioned and mapped to evidence:
demonstrated, practically used, familiar, missing, or do-not-claim. The report shows whether each is in the resume.
This is an internal diagnostic. **It is not an ATS score and does not predict whether an employer's ATS selects a resume.**

## Truthfulness
The claim guard compares resume text to the wiki: phrases and skills the candidate's audit marked Wrong are errors
(approval blocked unless forced); Unbacked ones are warnings; skills with no evidence at all are warnings.
Gaps stay gaps: a missing skill is never added.

## Not covered
Live link checking (links are checked structurally, not fetched), visual page rendering, and bullet rewriting by
algorithm: rewriting is done in a Claude Code session under `TAILOR.md`.
