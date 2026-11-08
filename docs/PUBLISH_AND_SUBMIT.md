# Publish and submit

The required deliverable is one **public GitHub repository URL**, not this ZIP.

1. Extract the ZIP locally. Open its `practo-capstone` folder.
2. Read `README.md`, set up Python 3.12, and run the tests/demo.
3. Create a new public repository on GitHub, for example `iitr-healthcare-capstone`.
4. Upload the **contents** of the extracted project folder to that repository. Do not upload the ZIP itself. `README.md` and `dataset.py` must appear at the repository root, with the other project directories beside them.
5. Commit all provided source, documents and evidence. Do not upload `models`, `.venv`, `.runtime` or cache folders created by running the project.
6. Open the repository in a logged-out/private browser window and confirm the README and evidence are visible.
7. In the LMS assignment, use the exact domain **Healthcare** and paste that public repository URL. Complete the LMS submission yourself before its displayed deadline.

If publishing from a terminal to a newly created empty repository:

```bash
git init
git add .
git commit -m "Complete Healthcare capstone with offline evidence"
git branch -M main
git remote add origin YOUR_PUBLIC_GITHUB_REPOSITORY_URL
git push -u origin main
```

Replace the placeholder with your real repository URL. GitHub authentication happens through your own approved Git setup; never paste a password or access token into source files.

For a fast review, start with `docs/EXPLAIN_AND_DEMO.md`, `evidence/RESULTS.md`, `evidence/pytest.txt`, and the sixteen-task map in `README.md`. The included evidence is from actual execution, not screenshots or fabricated examples.
