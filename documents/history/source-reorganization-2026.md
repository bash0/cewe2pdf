# Source reorganization (August 2026)

This note preserves background to the extraction of the original main module.
The [developer guide](../DEVELOPER_GUIDE.md#source-layout) describes the current layout.

In August 2026 the code was significantly rearranged into smaller files, to isolate functionality and make maintenance a little easier. Several improvements were made at the same time. The suite of pixel comparison suites was also extended. The code from cewe2pdf.py is basically still there and should be recognizable once you find the file in which it now lives. The work was done with the aid of OpenAI's Codex AI engine, which turned out to be very effective. Codex downloaded its own copy of the source structure from GitHub to the local machine, complete with tests, so that it could make its suggested changes first and run the test suite before making a final change proposal for whatever modification had been suggested.  
