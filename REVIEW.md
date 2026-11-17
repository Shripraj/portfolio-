# Stage 1: Resume consolidation and review items

Sources: the DOCX resume (`SHRIDHAR_PATIL.docx`), the PDF resume (`Shridhar.pdf`), and the project brief.
Where the brief and the resumes agree, the content is used as is. Where they differ, the item is listed below for your decision.

## Consolidated content (as seeded)

| Section | Source | Notes |
|---|---|---|
| Name, contact | Both resumes + brief | Phone, email, LinkedIn and GitHub agree across all sources. |
| Education | Both | B.E. CSE, S. G. Balekundri Institute of Technology, Belagavi, expected 2027. |
| Experience | DOCX (both roles), PDF (Vtricks) | Two entries. See review items 2 and 3. |
| Projects | Brief (all 7), PDF (4 projects), DOCX (3 projects) | Metrics come only from the resumes. Nothing is invented. |
| Skills | Both + brief | Merged and de-duplicated into 10 categories. |
| Certifications | Both + brief | 10 entries, each supported by at least one resume. |

## Items to confirm (REVIEW)

1. **Positioning conflict.** The PDF headline reads "Data Analyst | Excel | SQL | Python | Power BI". The brief sets Python Software Developer as primary. The site keeps Python as the default mode and gives Data Analyst its own mode, so both are available.
2. **She Can Foundation (Python Developer Intern)** appears only in the DOCX. Please confirm it belongs on the public site.
3. **Vtricks location** is "Hybrid" in the DOCX only. The site shows "Bengaluru (Hybrid)".
4. **Certifications.** "Excel – OneRoadmap" and "Data Science & ML – Udemy" appear only in the PDF. The two Forage job simulations (with February 2026 dates) appear only in the DOCX.
5. **Prompt-engineering course names differ.** The DOCX says "Foundations" and "Essentials". The PDF says "Essentials" and "Fundamentals". The site uses the DOCX names.
6. **RAG chatbot for Ground Reality.** Neither resume mentions it, so it is excluded, as the brief asks. Please send its implementation details if you want it added.
7. **Skills present in only one source.** The PDF lists Claude, GPT and Gemini under "AI Tools". The DOCX lists Core Skills (Data Structures, Problem Solving, Team Collaboration, Communication, Time Management). Both are included; remove any you don't want shown.
8. **PostgreSQL** appears in the brief and in the GlowGuide stack, but in neither resume's skill list. It is kept under Databases.
9. **Relativity / e-discovery.** The PDF summary says you are eager to learn these. It is left off the public site because it is not portfolio content. Say if you want it in the About text.
10. **Project coverage.** Four projects come from the PDF only, three from the DOCX only, and GoVigyan, Siksha and GlowGuide also appear in the brief. The DOCX gives no problem or solution statement for GlowGuide, so those fields are left empty.
11. **Missing project details (not invented, shown as gaps in admin):** GitHub repository URLs for each project, live demo URLs, screenshots, GlowGuide problem and solution, and certificate verification links.
12. **Resume files.** The uploaded PDF resume is seeded as the Data Analyst resume. The Python Developer resume needs a PDF upload through the admin dashboard.
13. **Reported metrics.** Figures are labelled "as reported in resume". Examples: GoVigyan 75–80% accuracy, and rainfall forecast within 4.1%. The live site shows them exactly as stated.

---

# Stage 2: Design direction

**Concept: "Editorial workbook."** A calm, printed-feeling portfolio. Working notes sit beside finished pieces, like a good design studio's index. It avoids product-landing-page tropes.

- **Palette (light, default):** background `#F5F2EB`, surface `#EAE6DD`, text `#24231F`, secondary text `#77736B`, olive accent `#78816A`, bronze `#B18A57`.
- **Palette (dark):** background `#20211E`, surface `#2B2C27`, bronze and olive shift up in lightness for contrast.
- **Type:** Playfair Display for the hero name and section titles only. Manrope for everything else. Generous line height (1.65 for body copy).
- **Layout:** 12-column grid. The projects section uses an editorial grid with three tile widths (large, medium, small) in a repeating rhythm. No two neighbouring tiles share a size, and there are no identical cards.
- **Career modes:** a segmented control in the hero switches Python Software Developer and Data Analyst. It changes the introduction, featured projects, project order, skill emphasis and the resume download.
- **Motion:** gentle scroll reveals that respect `prefers-reduced-motion`, underline hover states, and nothing that moves while text is being read.
- **Avoided:** gradients, glow, glassmorphism, blobs, fake progress bars, stock or AI portraits, and placeholder buttons. A profile photo is optional. Without one, the hero uses a typographic monogram.
