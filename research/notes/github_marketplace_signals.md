# GitHub, Open-Source and Gig-Marketplace Demand Signals for "Upload a File, Get a Finished Deliverable" AI Products

Research date: 2026-10-14. GitHub star and issue counts were pulled live from the GitHub REST search API (`api.github.com/search/repositories` and `/search/issues`, unauthenticated) on 2026-10-14. Format: repo, stars, open issues, last push. Fiverr/Upwork figures come from gig listing snippets returned by web search. Fiverr does not publish category-level order totals, so only per-seller signals were available.

## Q1: Which popular GitHub repos (2024-2026) turn files into deliverables, and do non-technical users struggle to install them or ask for a web version?

### Takeaway
Document-to-structured-output is one of the most-starred areas on GitHub (markitdown 190k, PaddleOCR 91k, MinerU 82k, marker 40k, PDFMathTranslate 37.5k, opendataloader-pdf 29.7k). But these tools produce developer outputs (Markdown/JSON for LLMs), not finished business deliverables like a tagged accessible PDF, a print-ready book, or a DWG. Explicit "please host this" issues are rare in the API results. The friction shows up instead as GUI/install/output-location issues, and maintainers selling their own hosted or paid tiers (Datalab for marker/surya/chandra, Immersive Translate for BabelDOC, OOMOL for pdf-craft, an enterprise PDF/UA add-on for opendataloader).

### Cited Findings
**Repo popularity (GitHub API, 2026-10-14):**
- Generic doc conversion / parsing: microsoft/markitdown 190,095 stars, 720 open issues. PaddlePaddle/PaddleOCR 91,062 stars ("Turn any PDF or image document into structured data for your AI"). opendatalab/MinerU 81,696 stars. paperless-ngx 46,642. datalab-to/marker 40,431 stars, 478 open issues. firecrawl/anydoc 22,813. datalab-to/surya 21,495 (OCR, layout, tables, 90+ languages). Unstructured-IO/unstructured 15,565. run-llama/liteparse 12,846. datalab-to/chandra 12,498 ("OCR model that handles complex tables, forms, handwriting"). — [GitHub API search "document ocr", "pdf to markdown", "ocr tables"](https://api.github.com/search/repositories?q=document+ocr&sort=stars)
- PDF accessibility: opendataloader-project/opendataloader-pdf 29,686 stars, pushed 2026-10-13, described as "PDF Parser for AI-ready data. Automate PDF accessibility. Open-source." — [GitHub API search "pdf accessibility"](https://api.github.com/search/repositories?q=pdf+accessibility&sort=stars)
- Its core is Apache-2.0 and does layout analysis plus auto-tagging, but PDF/UA export is a paid enterprise add-on. The open-source tool makes tagged PDFs, not certified PDF/UA output. — [opendataloader-pdf README via jsDelivr](https://cdn.jsdelivr.net/gh/opendataloader-project/opendataloader-pdf@main/README.md)
- Layout-preserving translation: PDFMathTranslate/PDFMathTranslate 37,539 stars, 165 open issues. windingwind/zotero-pdf-translate 12,045. immersive-translate 19,325. — [GitHub API search "pdf translate"](https://api.github.com/search/repositories?q=pdf+translate&sort=stars)
- The PDFMathTranslate/BabelDOC maintainers tell end users to use the hosted online service instead of the CLI. The hosted beta (Immersive Translate) offers 1,000 free pages/month. — [BabelDOC on PyPI](https://pypi.org/project/BabelDOC/); [BabelDOC GitHub](https://github.com/funstory-ai/BabelDOC)
- Scanned book to EPUB: oomol-lab/pdf-craft 6,372 stars, pushed 2026-10-12 ("will focus on" scanned books). — [GitHub API search "ebook formatting"](https://api.github.com/search/repositories?q=ebook+formatting&sort=stars)
- pdf-craft's LLM step can't run fully locally and needs a configured LLM service (DeepSeek recommended). Its only "hosted" path is as a node in OOMOL's workflow studio, where users drag "Analyse PDF" and "Generate EPUB" blocks. That is not a consumer upload page. — [DEV Community write-up](https://dev.to/githubopensource/pdf-craft-your-new-best-friend-for-scanned-pdf-conversion-4c02); [OOMOL blog](https://oomol.com/blog)
- Older book-scan cleanup tools are stale: phulin/rebook 150 stars, last push 2022-12-08. Tenrec-Builders/pi-scan 291 stars, last push 2018. — [GitHub API search "scanned book"](https://api.github.com/search/repositories?q=scanned+book&sort=stars)
- Bank statements: benjamin-awd/monopoly 427 stars ("converts bank statement PDFs to CSV"). StatementSensei 202 stars (PDF to CSV for bank statements). rheeloaded/paperpull 68. — [GitHub API search "bank statement pdf"](https://api.github.com/search/repositories?q=bank+statement+pdf&sort=stars)
- Table extraction: atlanhq/camelot 3,707 stars, last push 2023-01-05 (stale). img2table 898. — [GitHub API search "pdf table extraction"](https://api.github.com/search/repositories?q=pdf+table+extraction&sort=stars)
- Invoices/receipts: small, fragmented repos. receipt-parser-legacy 854 (last push 2024), bhimrazy/receipt-ocr 742, InvoiceableAI 46. — [GitHub API search "invoice parsing" / "receipt ocr"](https://api.github.com/search/repositories?q=receipt+ocr&sort=stars)
- Floor plans: CubiCasa/CubiCasa5k dataset 607 stars. cansik/architectural-floor-plan (AFPlan recognition) 401. Most top results are Home Assistant visualizers, not sketch-to-CAD converters. — [GitHub API search "floor plan"](https://api.github.com/search/repositories?q=floor+plan&sort=stars)
- Audio and ebooks to audiobooks: nazdridoy/kokoro-tts 1,931. lukaszliniewicz/Pandrator 633 ("Turn PDFs and EPUBs into audiobooks"). prakharsr/audiobook-creator 531. — [GitHub API search "pdf to audiobook"](https://api.github.com/search/repositories?q=pdf+to+audiobook&sort=stars)
- Subtitles/transcription: very crowded. SYSTRAN/faster-whisper 25,848. meetily 31,714. WhisperJAV 2,326. Many Chinese subtitle-generator repos with 800-1,700 stars. — [GitHub API search "subtitle generator" / "whisper transcription"](https://api.github.com/search/repositories?q=subtitle+generator&sort=stars)
- Resume parsing: xitanggg/open-resume 8,922 stars, last push 2024-10-29. JadeAI 1,992. — [GitHub API search "resume parser"](https://api.github.com/search/repositories?q=resume+parser&sort=stars)

**Non-technical friction (issue threads):**
- marker has many GUI-related issues from users who can't run or use the GUI: #460 "unable to run marker gui or through code" (2025-01), #554 "Where can I find the converted .md file using Streamlit's web GUI?" (2025-02), #575 ModuleNotFoundError when trying to use the GUI (2025-02), #859 "No output files option for marker_GUI?" (2025-09), #1087 asking whether GUI dependencies should be optional extras (2026-08). — [marker #554](https://github.com/datalab-to/marker/issues/554); [marker #460](https://github.com/datalab-to/marker/issues/460); [marker #575](https://github.com/datalab-to/marker/issues/575); [marker #859](https://github.com/datalab-to/marker/issues/859)
- A long-running request to "Create a Web/Windows version of Google OCR/Tesseract" for Tamil-language users (8 comments). This is an old (2019) example of non-English users wanting a no-install OCR. — [KaniyamFoundation/ProjectIdeas #80](https://github.com/KaniyamFoundation/ProjectIdeas/issues/80)
- Searching issues for "hosted version" in titles with "pdf" returned only 8 results, mostly unrelated. Searching issue bodies for "non-technical" in MinerU returned 0. — [GitHub issue search API](https://api.github.com/search/issues?q=%22hosted+version%22+in:title+pdf)

### Inferences
- Users rarely ask maintainers directly to "host it." The demand signal is indirect: star counts in the tens of thousands plus GUI and setup confusion. The strongest repos are already monetized by their own maintainers (Datalab, Immersive Translate, OOMOL, opendataloader enterprise). Generic "PDF to Markdown/JSON" is therefore not an open gap.
- The gap is the last mile from AI-ready output to a finished, standards-compliant deliverable: PDF/UA-tagged file plus audit report, KDP-valid print PDF plus EPUB, clean reflowable EPUB from a scan, DWG from a sketch. OSS covers the hard parsing. Nobody packages it as a done-for-you upload page for a non-technical buyer.
- Open-source maturity is low in floor-plan vectorization, receipt/invoice parsing and book-scan cleanup (stale or small repos). A product there needs more original ML work, and fewer free self-host alternatives undercut it.

### Gaps
- The GitHub search API rate limit (10/min unauthenticated, no `gh` CLI installed) prevented a broader issue sweep, for example "web version" or "online" issues across MinerU, PaddleOCR and pdf-craft, plus reaction counts.
- Hacker News "Ask HN/Show HN" threads were not found for these niches. One search for scanned-book-to-EPUB Show HN posts returned nothing relevant.

## Q2: Which Fiverr/Upwork "send me your file, I return a finished file" gig categories have large, steady paid demand, and at what prices?

### Takeaway
Many file-in, file-out gigs cluster at $10-$100 per job on Fiverr: PDF to Word/Excel retyping, KDP formatting, floor-plan redraws, Europass/Lebenslauf CVs, visa SOPs and deck redesigns. Agency-priced work runs much higher: PDF accessibility remediation at $5-$12+ per page and deck redesigns at $400-$600. Data Entry ranks #2 in Upwork's Customer Service & Admin category for 2026. Fiverr category-wide order counts are not public, so volume evidence is per seller.

### Cited Findings
- **PDF to Word / scanned retyping:** Most gigs are "Up to $50" with 1-3 day turnaround. Basic packages cover about 10 pages, and extra pages cost more. One seller has 736 orders completed, another 209 reviews at 5.0. Sellers commonly exclude handwritten or poor-quality scans, and one advertises "manual, no software or AI." — [Fiverr gig: retype scanned docs](https://fiverr.com/asifjadoon35/convert-pdf-to-docx-in-24-hours-71e5); [Fiverr seller ahmedali705](https://www.fiverr.com/ahmedali705); [Fiverr gig: scanned PDF to Word](https://fiverr.com/rennerlee/convert-a-scanned-pdf-to-word)
- **Data entry demand (Upwork):** Upwork's In-Demand Skills 2026 report (released 2026-02-04) lists Data Entry second in Customer Service & Admin Support, behind General Virtual Assistance. AI data annotation and labeling grew +154%. — [Upwork press release](https://www.upwork.com/press/releases/upworks-in-demand-skills-2026-demand-for-top-ai-skills-more-than-doubles-as-ai-is-embedded-into-everyday-work)
- **KDP book formatting:** Starting prices run from about $10 to $85, mostly $25-$50. A Top Rated gig at $85 covers KDP, IngramSpark paperback and ebook. Deliverables are a print-ready PDF plus EPUB, clickable TOC and front/back matter. Tables and images cost extra, and editing is excluded. A dedicated "fix KDP formatting errors" gig niche exists. — [Fiverr KDP gig](https://fiverr.com/quill_echo/format-your-kdp-paperback-and-ebook-interior-for-amazon); [Fiverr "fix KDP formatting errors"](https://fiverr.com/stacey_donlad/fix-kdp-formatting-errors-book-formatting-for-amazon-kdp-paperback-formatting); [Fiverr paperback formatting category](https://block.fiverr.com/gigs/paperback-formatting?page=18)
- **Floor plan redraw (sketch/PDF to 2D or DWG):** Most gigs are "Up to $50", one is $50-$100, and about $20 buys a single-level basic house in AutoCAD. Inputs are sketches, PDFs, Matterport scans or images. Outputs are DWG, PDF or JPG. — [Fiverr floor plan redraw](https://fiverr.com/qualityismylife/redraw-2d-floor-plan-for-you); [Fiverr PDF to DWG](https://fiverr.com/sanowarr/convert-pdf-into-cad-dwg-file); [Fiverr sketch to plan](https://fiverr.com/edo_1992/sketch-to-clean-floor-plan-conversion)
- **Europass / German Lebenslauf CVs (EU/DACH region-specific):** A Europass conversion gig costs $50 with 1-day delivery. German CV gigs are "up to $50" with 2-3 day delivery, and a bilingual DE/EN CV costs $50-$100. Tiered packages bundle CV, cover letter and LinkedIn. One DACH-focused seller works from a LinkedIn export. — [Fiverr Europass conversion](https://fiverr.com/m_baqir786110/make-europass-resume-cv); [Fiverr German CV](https://fiverr.com/paula_guentgen/write-your-german-cv); [Fiverr Lebenslauf](https://fiverr.com/andynamic/create-your-cv-lebenslauf); [Fiverr Europass + ATS](https://fiverr.com/foxtrot2/write-a-professional-europass-cv-and-ats-optimized-resume)
- **Student visa SOPs (South Asia sending to Canada/UK/Australia/EU):** Fiverr SOP gigs are "Up to $50" with 2-10 day delivery. Freelancer.com buyers post visa SOP jobs at ₹600-1,500 INR (Australia engineering SOP), and one bid for a French student visa SOP was ₹1,500 for 1-day delivery. — [Fiverr SOP gig](https://fiverr.com/syedraza0222/write-sops-for-you); [Freelancer Australia visa SOP](https://www.freelancer.ie/projects/research-writing/australia-graduate-engineering-study); [Freelancer French visa SOP](https://www.freelancer.co.th/projects/writing/french-student-visa-sop-writer)
- **Pitch deck / PowerPoint redesign (existing deck in, redesigned deck out):** Prices run from up to $50 (2-4 days), through $100-$200 (7 days), to $400-$600 (9 days) for full refreshes. — [Fiverr deck redesign](https://fiverr.com/chachan234/redesign-your-powerpoint-presentation); [Fiverr pitch deck redesign](https://www.fiverr.com/s/e6ZVp1E)
- **PDF accessibility remediation (agency market, US-driven):** Accessible.org charges $7.50-$11.50/page (formerly $4.00-$11.50). Allyant charges $5-$8/page and Skynet $5/page base. EqualWeb charges $1-$4/page (low end). Venngage puts the average at $5-$25/page. Equalify (March 2026) says $1-$11.50, with most vendors at $5-$8. Automated checkers catch only 20-30% of issues. — [Accessible.org pricing](https://accessible.org/pricing/); [Venngage PDF accessibility cost](https://venngage.com/blog/pdf-accessibility-cost/); [Equalify sources](https://equalify.uic.edu/EqualifyEverything/equalify-docs/blob/main/reflow/sources.md); [Skynet cost factors](https://www.skynettechnologies.com/blog/pdf-accessibility-cost-factors)
- **Regulatory driver:** DOJ's interim final rule moved ADA Title II (WCAG 2.1 AA) compliance from 2026-04-24 to 2027-04-26 for entities serving 50k+ people, and to 2028-04-26 for smaller entities. The substantive requirements are unchanged, and PDFs are covered. DOJ cited "limitations in current technology, including limits of generative AI for remediation" as a reason. — [Plante Moran](https://plantemoran.com/explore-our-thinking/insight/2026/04/doj-extends-ada-title-ii-web-accessibility-compliance-deadlines); [JD Supra](https://www.jdsupra.com/legalnews/ada-title-ii-web-accessibility-3432173/); [Archer Law PDF](https://www.archerlaw.com/print/v2/content/11506/doj-extends-ada-web-accessibility-deadline-to-april-2027.pdf)

### Inferences
- Per-job prices of $20-$50 mean an AI product must charge about $5-$30 per file, or a subscription, to undercut freelancers. PDF accessibility is the exception: $5-$12 per page makes a 50-page document cost $250-$600, so an AI-plus-human-review service at $1-$3 per page has large margin room.
- Sellers excluding handwritten and bad scans is a capability boundary that newer OCR models (chandra, surya) target. That segment is underserved by both freelancers and cheap converters.
- The DOJ delay extends the accessibility buying window through 2027-2028 rather than killing it. Smaller US public bodies (school districts, small towns, special districts) have until 2028 and limited budgets, which suits a self-serve product.

### Gaps
- Fiverr does not expose category-wide order counts or the number of active gigs per category in the retrieved pages. "Large, steady demand" is supported only by per-seller order and review counts and by Upwork's Data Entry ranking.
- No reliable Fiverr data was found specifically on PDF/WCAG remediation gigs, LinkedIn rewrite volumes or transcript-cleanup gigs.
- No Canada- or UK-specific SOP price points from Fiverr.

## Q3: For each idea, what are the current SaaS competitors (names, pricing), how good are they, and how open is the gap?

### Takeaway
Of 12 candidate ideas, the best-evidenced openings are PDF accessibility remediation for small US public entities and SMBs (weak self-serve competitors), scanned book to clean EPUB (open gap), done-for-you KDP formatting from an uploaded .docx (weak competitors: DIY desktop tools only), and floor-plan sketch/PDF to DWG (weak competitors, harder tech). Bank statement conversion, layout-preserving PDF translation, subtitles and generic PDF to Word are already crowded.

### Cited Findings
**Idea 1: PDF accessibility remediation (WCAG 2.1 AA / PDF/UA tagged PDF plus compliance report). Region: US first (ADA Title II, Section 508); the EU Accessibility Act is a likely second market. Label: WEAK COMPETITORS (enterprise and quote-based).**
- PREP (Continual Engine) does AI tagging, reading order, OCR and alt-text with quote-only pricing and no free plan. Its claimed 95% auto-tag accuracy is a vendor claim, and Continual Engine also publishes the rankings that list PREP first. — [iTechGuides PREP](https://www.itechguides.com/products/prep/); [Continual Engine tools list](https://www.continualengine.com/blog/best-pdf-remediation-tools/)
- Fruition charges $0.50/page basic, $2/page for full AI remediation, and gives 10 free pages/month. — [Fruition PDF accessibility](https://www.fruition.net/ai-platforms/pdf-accessibility)
- Nutrient DWS Accessibility API is a developer API that auto-tags and validates, with no storage of files. — [Nutrient](https://nutrient.io/api/accessibility-api/)
- QyrosXS sells on AWS Marketplace and targets governments. — [AWS listing](https://aws.amazon.com/marketplace/pp/prodview-ynb6jp67w7oqe)
- A PDF Association talk (2025) argues that the best results come from AI bulk tagging plus human review, not full automation. — [PDF Association presentation](https://pdfa.org/wp-content/uploads/2025/10/0-3-16_15-AnnKnettler-Beyond_Automation.pdf)
- OSS base: opendataloader-pdf (29.7k stars) with PDF/UA export behind a paid add-on. — [README](https://cdn.jsdelivr.net/gh/opendataloader-project/opendataloader-pdf@main/README.md)

**Idea 2: Scanned book or PDF to clean, reflowable EPUB (and Markdown). Region: worldwide, strong in CJK given pdf-craft's origin. Label: OPEN GAP (no polished consumer upload service found).**
- pdf-craft (6.4k stars) is hosted only as an OOMOL workflow node, and the closest alternative is a Claude Code skill for text-layer PDFs. No Show HN hosted service was found. — [DEV write-up](https://dev.to/githubopensource/pdf-craft-your-new-best-friend-for-scanned-pdf-conversion-4c02); [pdf-to-epub skill README](https://cdn.jsdelivr.net/gh/koreyba/Claude-Skill-pdf-to-epub@master/README.md)
- Caveat: copyright and DRM risk for scanned books. The clean market is public-domain, self-published and institutional content.

**Idea 3: Done-for-you KDP/IngramSpark formatting (.docx in, print-ready PDF plus EPUB that passes KDP validation out). Region: worldwide, English-first. Label: WEAK COMPETITORS (only DIY tools).**
- Kindle Create is free, but its design ceiling is low and its .KPF output is Amazon-only. Atticus costs $147 one-time and runs cross-platform plus browser. Vellum costs $199.99 (ebook) or $249.99 (with print) and runs on Mac only. None replaces a service for heavily illustrated or complex books. — [publishing.co.uk comparison](https://www.publishing.co.uk/guides/atticus-vs-vellum-vs-kindle-create/); [Kindlepreneur Atticus vs Vellum](https://kindlepreneur.com/atticus-vs-vellum/); [Scribecount](https://scribecount.com/author-resource/writing-tools-for-authors/atticus-vs-vellum-vs-lacuna-vs-kindle-create)
- Fiverr demand: $10-$85 per book, plus a "fix KDP formatting errors" niche (cited in Q2).

**Idea 4: Floor plan sketch, photo or PDF to clean 2D plan or DWG. Region: worldwide; real-estate listing plans are common in UK/EU/AU. Label: WEAK COMPETITORS (but technically hard).**
- CubiCasa is scan-based (phone walkthrough) and, according to competitor RoomSketcher, doesn't redraw existing sketches. RoomSketcher offers a paid human redraw with next-business-day turnaround. — [RoomSketcher comparison](https://www.roomsketcher.com/?p=18545); [CubiCasa on Capterra](https://www.capterra.com/p/193054/CubiCasa/)
- OSS is immature (CubiCasa5k dataset 607 stars, AFPlan 401). Fiverr gigs cost $20-$100 (cited above).

**Idea 5: Bank statement PDF to CSV/Excel/QBO for accountants. Region: worldwide; bank-specific layouts are regional. Label: ALREADY CROWDED.**
- DocuClipper charges about $0.05/page (2024 tiers: $39/mo for 200 pages, $74/500, $159/2,000) and itself names competitors Nanonets, Docsumo, Dext ($1.6-$3.8/page per DocuClipper), Hubdoc ($12/client) and MoneyThumb ($0.20/page). All of these figures are DocuClipper's own marketing claims. — [DocuClipper pricing](https://www.docuclipper.com/pricing); [DocuClipper vs Dext](https://docuclipper.com/comparisons/docuclipper-vs-dext-prepare); [DocuClipper vs MoneyThumb](https://blog.docuclipper.com/comparisons/docuclipper-vs-moneythumb/)
- OSS: monopoly 427 stars and StatementSensei 202 stars (cited in Q1).

**Idea 6: Scanned or messy PDF to faithfully formatted editable Word/Excel (including handwriting and bad scans). Label: CROWDED for clean digital PDFs, WEAK for bad scans and handwriting.**
- Fiverr freelancers avoid handwritten and poor scans (cited in Q2). The newer OSS models chandra (12.5k) and surya (21.5k) target handwriting, forms and complex tables, and Datalab (their maintainer) sells hosted access. — [GitHub API "ocr tables"](https://api.github.com/search/repositories?q=ocr+tables&sort=stars)

**Idea 7: Layout-preserving PDF translation (papers, manuals). Label: ALREADY CROWDED.**
- Immersive Translate hosts BabelDOC with 1,000 free pages/month. A Pro quota of 10,000 pages is reported by a third-party blog only. — [BabelDOC PyPI](https://pypi.org/project/BabelDOC/); [kocpc blog](https://en.kocpc.com.tw/?p=11093)

**Idea 8: Europass / German Lebenslauf / country-format CV conversion (existing CV or LinkedIn PDF in, country-compliant CV out). Region: EU/DACH, plus Indian, Pakistani and Nigerian applicants targeting the EU. Label: WEAK-TO-CROWDED.**
- Fiverr: $50 Europass conversion, $50-$100 bilingual DE/EN (cited in Q2). No dedicated SaaS competitor pricing was retrieved.

**Idea 9: Student visa SOP drafting from transcripts and CV. Region: South Asia and Africa sending to Canada/UK/AU/EU. Label: CROWDED (general chatbots), low price ceiling (₹600-1,500), plus integrity and authenticity risk with visa officers.**
- Pricing evidence is cited in Q2. No SaaS competitor data was retrieved.

**Idea 10: Existing pitch deck (.pptx/PDF) to redesigned deck. Label: CROWDED (likely AI presentation tools; not verified in this pass).**
- Fiverr prices are $50 to $600 (cited in Q2).

**Idea 11: Ebook or PDF to audiobook for indie authors. Label: CROWDED-ish.**
- OSS: Pandrator 633 stars, audiobook-creator 531, kokoro-tts 1.9k (cited in Q1). No SaaS pricing was retrieved.

**Idea 12: Subtitle/SRT generation and translation. Label: ALREADY CROWDED.**
- Many repos exist (faster-whisper 25.8k, WhisperJAV 2.3k, many 800-1,700-star Chinese tools) (cited in Q1).

### Inferences
- Ranking by evidence strength of "paid demand + weak hosted competition": (1) PDF accessibility for small public entities and SMBs, (2) KDP done-for-you formatting, (3) scanned book to EPUB, (4) floor-plan to DWG, (5) bad-scan or handwriting to Word/Excel. These share a pattern: buyers pay for a standards-valid artifact (PDF/UA, KDP validator, DWG), which generic chat AI doesn't reliably produce. That creates a moat beyond "call an LLM."
- Ideas 9 and 10 (SOP, deck) are easily done in general chat AI or existing AI slide tools, so willingness to pay for a dedicated upload product is likely low.
- For accessibility, DOJ's own statement that generative AI has limits implies buyers will want a human-verified or audit-report tier. A hybrid "AI + reviewer" service at $1-$3/page undercuts the $5-$12/page agencies.

### Gaps
- No competitor pricing was verified for Europass/CV tools, SOP tools, AI deck redesign tools (e.g. Gamma, Beautiful.ai) or audiobook SaaS (e.g. ElevenLabs). The labels for ideas 8-12 rely on GitHub density and general-chat-AI substitutability, not verified competitor pages.
- There's An AI For That and Product Hunt saturation checks were not performed within the tool-call budget.
- Accuracy of AI PDF remediation tools (PREP's 95% claim, Fruition) is unverified by independent benchmarks.
