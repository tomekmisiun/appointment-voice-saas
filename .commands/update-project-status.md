# Command: Update Project Status

Copy everything below the line into your agent chat.

---

Update project tracking files after **completed, verified work** in fastapi-production-foundation.

**Merged PR or work summary:**  
<PASTE PR LINK OR BULLET LIST OF CHANGES>

**Instructions:**

1. Read `.ai-rules/documentation.md` and `.ai-rules/review.md`.
2. Update only what the work actually changed:
   - `PROJECT_STATUS.md` — verified capabilities (code + tests exist)
   - `ROADMAP.md` — task Status → Done when verified; add PR to historical table if merged
   - `TECH_DEBT.md` — Status → Done with same change set; fix summary counts if needed
   - `README.md` — only if setup, API, env, workflows, or known gaps changed
3. Do **not** mark planned work complete without verification.
4. Do **not** duplicate rule bodies into tracking files.
5. Run `make validate` if test counts or capability claims changed; cite current pytest count accurately.

Output: list of files edited and a short changelog for the user.
