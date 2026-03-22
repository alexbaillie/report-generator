# PsychReportGen Psychologist Quick Start

This guide is for psychologists using PsychReportGen to create and export reports.

## What this app does

- Helps you draft psychological reports using a clinic template.
- Generates section drafts using local AI.
- Saves reports locally and lets you export them to a text file.

AI output is a draft. Always review and edit before finalizing.

## App tabs (what each one is for)

PsychReportGen uses a left sidebar to switch between tabs.

- **Home**
  - A simple starting page.
  - If you’re not sure where to go, start here, then select **New Report**.
- **New Report**
  - Where you create a new report from a clinic template.
  - Fill out the form fields and generate section drafts.
- **Text Editor**
  - A general-purpose writing area.
  - Use this if you want to draft or rewrite text with AI assistance outside the report form.
  - It does not replace clinical review.
- **Reports**
  - Where all previously generated reports are listed.
  - Open a report to review it, and use **Export** to download a `.txt` file.
- **Templates**
  - Where report templates are managed.
  - Most psychologists will not need to change templates. If your clinic manager asks you to use a specific template, select it in **New Report**.

## Quick start (first report)

### 1) Start the app

- Open PsychReportGen.
- Wait until you see the main screen (the app may show “Starting Application…” for a short time).

### 2) Create a new report

1. Go to **New Report**.
2. Choose a template from **Choose template**.
   - If the clinic has a Default template, it may be preselected.
3. Fill in the form section-by-section.

### 3) Tests Administered (tables)

If you see a section called **Tests Administered (Upload or Paste Score Tables)**:

- Use the dropdown to pick the test name.
- Use **Upload** to add files, or
- Paste a table directly (from Excel/Google Sheets).
  - A preview table should appear after pasting.
- Add optional notes if needed.

Tip: If the test isn’t listed, choose **Other** and type the test name.

### 4) Generate section drafts

- When you submit/generate, the app drafts sections one at a time.
- A progress message appears (for example: “Generating … section…”).

If a section has no information filled in, it may be skipped.

### 5) Review the report

After generation, the app opens the saved report.

- Read through each section carefully.
- Correct phrasing, add missing clinical details, and ensure accuracy.

## Viewing and exporting reports

1. Go to **Reports**.
2. Select a report from the list.
3. Select **Export** to download a `.txt` file.

Tip: After exporting, you can paste the text into Word/Google Docs for formatting.

## Good habits for best AI results

- Use the template fields as intended (short, clear inputs work best).
- Avoid leaving critical details only in long free-text when a specific field exists.
- If the AI output includes something that wasn’t provided, remove it.
- Keep an eye out for:
  - incorrect dates/ages
  - invented scores
  - diagnoses that were not confirmed

## Simple troubleshooting

### The app stays on “Starting Application…”

- Close the app.
- Re-open the app.
- If it still happens, share this log file with your clinic support person:
  - `C:\Users\<your-username>\report-generator-backend.log`

### AI generation fails or returns nothing

- Try again once.
- If it continues:
  - Close and re-open the app.
  - Let your clinic support person know what you were trying to generate.

### Pasting a table didn’t work

- Try copying the table again from Excel/Sheets.
- Paste directly into the table box.
- If needed, export the table as CSV and upload it.

### A section didn’t generate

Common reasons:

- The section had no filled fields.
- The text was too minimal to draft from.

Try adding a few key bullet points or sentences and generate again.

## Safety reminder

Treat all AI-generated text as a draft. You are responsible for:

- clinical accuracy
- appropriate language
- confidentiality and documentation standards
