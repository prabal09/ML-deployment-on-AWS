# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A personal reference collection of **LaTeX-authored guides** on deploying ML models to AWS. There is no application code — each `.tex` is a standalone article and its compiled `.pdf` sits alongside it. Not a git repo.

Three documents, one per deployment path:

| Source | Output | Topic |
|---|---|---|
| [ml_sagemaker.tex](ml_sagemaker.tex) | [ml_sagemaker.pdf](ml_sagemaker.pdf) | SageMaker (real-time, serverless, async, batch) |
| [lambda_ecr.tex](lambda_ecr.tex) | [lambda_ecr.pdf](lambda_ecr.pdf) | Lambda container images from ECR |
| [ecr_eks.tex](ecr_eks.tex) | [ecs_eks.pdf](ecs_eks.pdf) | ECS (Fargate) and EKS |

Note the naming mismatch on the third pair: the source is `ecr_eks.tex` but the PDF is `ecs_eks.pdf`. Preserve both names as-is unless the user asks to rename — external links may already point at them.

## Building the PDFs

Each document is self-contained (no shared `.sty`, no bibliography, no external figures). Compile with `pdflatex`; run it twice so the TOC and internal `\ref`s resolve:

```powershell
pdflatex ml_sagemaker.tex ; if ($?) { pdflatex ml_sagemaker.tex }
```

TeX Live and MiKTeX both work. Required packages are all mainstream: `hyperref`, `xcolor`, `listings`, `enumitem`, `graphicx`, `titlesec`, `tcolorbox`, `array`, `booktabs`, `longtable`.

## Conventions shared across all three docs

Any new document (or edits to an existing one) should follow the preamble already established in the three files, so they render consistently:

- **Callout boxes** — use these instead of inventing new ones:
  - `\begin{notebox}` … blue, general context
  - `\begin{warnbox}` … orange, "Important" — hard constraints, footguns
  - `\begin{tipbox}` … green, recommendations / rules of thumb
- **Code listings** — use the pre-defined styles, don't redefine language settings inline:
  - `[style=pycode]` for Python (numbered lines)
  - `[style=bashcode]` for shell / AWS CLI
  - `[style=dockercode]` for Dockerfiles (defined in `lambda_ecr.tex` and `ecr_eks.tex`)
  - `[style=jsoncode]` for JSON policy documents (defined in `lambda_ecr.tex` and `ecr_eks.tex`)
- **Structure** — every doc opens with Introduction → Core Concepts / Constraints → Prerequisites → numbered `Step N ---` subsections → Production Best Practices → Troubleshooting Checklist → Summary. Keep this shape when adding content.
- **Author metadata** — `pdfauthor={Prabal}` in `\hypersetup`; `\author{Prabal}` on the title page.

If you need `dockercode` or `jsoncode` in `ml_sagemaker.tex`, copy the `\lstdefinelanguage` + `\lstdefinestyle` blocks from `lambda_ecr.tex` — they are not currently defined in the SageMaker doc.

## Editing guidance

- The code snippets in the listings are **illustrative**, not executable — don't try to run or lint them. Treat them as documentation prose.
- When adding a new deployment path, create a new `.tex` at the repo root using one of the existing files as a template rather than factoring out a shared preamble; the three docs deliberately duplicate their preambles to stay self-contained.
- Regenerate the corresponding PDF after any `.tex` edit so the two stay in sync (both are committed to the working tree).
