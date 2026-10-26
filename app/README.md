# meltinv web app

A one-page website for people who do not use Python: upload an `.xlsx` or `.csv`
file, choose the options, run meltinv, and download a `.zip` with the results
tables, figures, a plot archive and a short README. [Tutorial 1](../tutorials/01_web_app.md)
walks a new user through it. The app is
[`streamlit_app.py`](streamlit_app.py); its look is set in
[`.streamlit/config.toml`](.streamlit/config.toml).

Each run happens in its own temporary folder, in a separate process, and the
folder is deleted as soon as the run finishes. Several people can use the site
at once without seeing each other's files.

## Run it on your own computer

From the repository folder, install meltinv with the app's extra packages, then
start the app:

```bash
pip install -e ".[app]"
streamlit run app/streamlit_app.py
```

Your browser opens at http://localhost:8501. Stop the app with Ctrl+C.

## Put it online for free (Streamlit Community Cloud)

[Streamlit Community Cloud](https://streamlit.io/cloud) hosts Streamlit apps for
free, straight from a public GitHub repository. Its free resources (up to about
2.7 GB of memory) are enough for meltinv.

**Before you start:** the website is built from the `main` branch on GitHub, so
push your latest changes first.

1. Go to https://share.streamlit.io and click **Continue with GitHub**. Sign in
   as the owner of the `meltinv` repository and allow Streamlit to read it.
2. Click **Create app**, then **Yup, I have an app**, and fill in:
   - **Repository:** `shihao-jiang/meltinv`
   - **Branch:** `main`
   - **Main file path:** `app/streamlit_app.py`
   - **App URL:** `meltinv`, which gives **https://meltinv.streamlit.app**. If that
     name is taken, choose another; you can change it later.
3. Click **Advanced settings** and set **Python version** to **3.12**. Newer
   versions do not work yet, because meltinv needs NumPy 1.x. Click **Save**.
4. Click **Deploy**. The first build installs meltinv and meltPT and takes about
   5–10 minutes; a log on the right shows its progress. The website opens when
   it is ready.
5. Test it with the example data: click **Download example data**, upload that
   file and click **Run meltinv**.

The app installs its packages from [`requirements.txt`](requirements.txt), which
points at meltinv's `main` branch on GitHub.

### Updating the website

Push your changes to `main` on GitHub; the website updates itself within a few
minutes. If it still shows the old version, open the app, click **Manage app**
(bottom right, visible only to you when signed in), then **⋮ → Reboot app**.

### If the build fails

Open **Manage app** to read the log. Common causes:

- **Python version:** choose 3.12 in the app's **Settings → General** and reboot.
- **A package fails to install:** copy the last 30 lines of the log, open an
  issue on GitHub or ask a developer.

## Cost, limits and how long it lasts

- **Cost:** free; Streamlit asks for no payment details.
- **Sleeping:** an app with no visitors for 12 hours goes to sleep. The next
  visitor sees a **"Yes, get this app back up!"** button; after about a minute,
  the site works normally. Nothing is lost.
- **Resources:** up to about 2 CPUs and 2.7 GB of memory, shared fairly between
  visitors. Streamlit says these limits may change without notice.
- **How long it lasts:** there is no expiry date, but it is a free service whose
  terms can change, as Hugging Face's free tier did in July 2026. In the paper,
  cite the GitHub repository (or a Zenodo archive of it) as the permanent
  record, and the website as a convenience.
- **Size limits set in the app:** 3,000 samples per file, and individual
  per-sample figures for up to 300 samples. Change `MAX_SAMPLES` and
  `MAX_INDIVIDUAL_FIGURES` at the top of `streamlit_app.py`.
- **Run times:** about a minute for the 38-sample example with the olivine
  correction. The correction dominates: roughly a third of a second per
  sample, against about a minute per 1,000 samples for the inversion alone.

## Other hosting

[`huggingface/`](huggingface) holds a Docker image definition and Space README
for any host that runs containers: a Hugging Face Docker Space (which needs a
paid plan since July 2026) or your own server. Copy both files into the Space,
or build the `Dockerfile` with Docker.

## Changing the look

All colours are in [`.streamlit/config.toml`](.streamlit/config.toml):
`primaryColor` for the buttons, `secondaryBackgroundColor` for panels. Edit the
values, restart the app, and reload the page. The text on the page is in
`streamlit_app.py`; edit it like any other text, keeping the quotation marks.

## Privacy

Uploaded files are processed in a temporary folder that is deleted after each
run, and the app never saves them anywhere else; the results stay in the
server's memory only for that browser session. The server itself runs on
Streamlit's (Snowflake's) computers, so anyone who should not upload unpublished
data can run the app on their own computer, as above.
