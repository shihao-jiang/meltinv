# meltinv web app

A one-page website for people who do not use Python: upload an `.xlsx` or `.csv`
file, choose the options, run meltinv, and download a `.zip` with the results
tables, figures, a plot archive and a short README. The app is
[`streamlit_app.py`](streamlit_app.py); its look is set in
[`.streamlit/config.toml`](.streamlit/config.toml).

Each run happens in its own temporary folder, in a separate process, and the
folder is deleted as soon as the run finishes. Several people can use the site
at once without seeing each other's files.

## Run it on your own computer

From the repository folder, install meltinv with the app's extra packages, then
start the app from this folder:

```bash
pip install -e . -r app/requirements.txt
cd app
streamlit run streamlit_app.py
```

Your browser opens at http://localhost:8501. Stop the app with Ctrl+C.

## Put it online for free (Hugging Face Spaces)

[Hugging Face Spaces](https://huggingface.co/spaces) hosts small web apps for
free. The free hardware (2 CPUs, 16 GB of memory) is more than meltinv needs.

**Before you start:** the Space builds the app from the `main` branch on GitHub,
so push this `app/` folder to GitHub first.

1. Create a free account at https://huggingface.co/join.
2. Go to https://huggingface.co/new-space and fill in:
   - **Space name:** `meltinv`. The address will be
     `https://huggingface.co/spaces/<your-user-name>/meltinv`.
   - **License:** MIT.
   - **Space SDK:** **Docker**, then the **Blank** template.
   - **Space hardware:** **CPU basic · 2 vCPU · 16 GB · FREE**.
   - **Visibility:** Public.
3. Click **Create Space**.
4. In the new Space, open the **Files** tab, choose **Add file → Upload files**,
   and upload the two files in [`huggingface/`](huggingface): `Dockerfile` and
   `README.md`. Replace the `README.md` the Space created. Click **Commit**.
5. The Space builds itself; follow it in the **Logs** tab. The first build
   takes about 5 minutes. When it says **Running**, the website is live.
6. Test it with the example data: on the website, click **Download example data**,
   upload that file and click **Run meltinv**.

### Updating the website

Push your changes to `main` on GitHub. Then, in the Space, open
**Settings → Factory rebuild**. A normal restart reuses the old copy of the code;
a factory rebuild downloads the new one. To publish a fixed version instead of
the latest `main`, change `MELTINV_REF=main` in the Space's `Dockerfile` to a tag
such as `v0.1.0`.

## Cost, limits and how long it lasts

- **Cost:** free on the free CPU hardware. Hugging Face asks for no payment
  details for it.
- **Sleeping:** a free Space goes to sleep after 48 hours without visitors. The
  next visitor sees a "starting" page for a minute or two, after which it works
  normally. Nothing is lost when it sleeps.
- **How long it lasts:** as long as your Hugging Face account and their free tier
  exist. There is no expiry date, but it is a free service with no guarantee, so
  in the paper cite the GitHub repository (or a Zenodo archive of it) as the
  permanent record, and the website as a convenience.
- **Size limits set in the app:** 3,000 samples per file, and individual
  per-sample figures for up to 300 samples. Change `MAX_SAMPLES` and
  `MAX_INDIVIDUAL_FIGURES` at the top of `streamlit_app.py`.
- **Run times on the free hardware:** about a minute for the 38-sample example
  with the olivine correction. The correction dominates: roughly 10 minutes
  for 1,800 samples, compared with under a minute for the inversion alone.

## Changing the look

All colours are in [`.streamlit/config.toml`](.streamlit/config.toml):
`primaryColor` for the buttons, `secondaryBackgroundColor` for panels. Edit the
values, restart the app, and reload the page. The text on the page is in
`streamlit_app.py`; edit it like any other text, keeping the quotation marks.

## Privacy

Uploaded files are processed in a temporary folder that is deleted after each
run, and the app never saves them anywhere else; the results stay in the
server's memory only for that browser session. The server itself runs on
Hugging Face's computers, so anyone who should not upload unpublished data can
run the app on their own computer, as above.
