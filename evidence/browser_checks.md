# CareDesk browser verification

The actual FastAPI backend was opened through the managed local preview in the browser. These were live HTTP requests from the interface, not replayed responses.

- Home screen loaded local CSS/JavaScript and reported Backend connected.
- Suggested appointment question returned APT-003, Scheduled, INR 1500, and the cancellation policy.
- Execution panel displayed five actual agent roles and both executed tools.
- Citation button opened the original cancellation policy in an accessible dialog; Close returned to chat.
- “What is its fee?” resolved APT-003 in the same session.
- Repeat last question returned a cache hit; all five agents displayed “Not run · cached response”.
- New conversation followed by “What is its fee?” requested a reference rather than inheriting the old session.
- Project overview displayed the original dataset/framework design and recorded evaluation results with limitations.
- Desktop chat and overview layouts were visually inspected. Responsive breakpoints are implemented; a separate mobile-device run was not performed.
- All 92 backend tests passed, including the new presentation/execution-metadata test. JavaScript syntax passed `node --check`.

No screenshot or binary asset is included in the assignment package. The UI is an optional presentation layer over the required backend; Swagger remains at `/docs`.
