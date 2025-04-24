# Application Flow

Here is a flowchart illustrating the main workflow of the SOC Screenshot & Annotation Tool.

```mermaid
graph TD
    A[Start Application] --> B{Select Area?};
    B -- Yes --> C[Start Region Selection];
    C --> D[Capture Selected Region];
    D --> E[Display Screenshot on Canvas];
    E --> F{Add Annotations?};
    F -- Yes --> G{Annotation Type?};
    G -- Text --> H[Add Text Annotation];
    G -- Rectangle --> I[Add Rectangle Annotation];
    H --> F;
    I --> F;
    F -- No --> J{Save or Upload?};
    J -- Save Locally --> K[Save Image to File];
    J -- Upload to SN --> L{ServiceNow Configured?};
    L -- Yes --> M[Get Ticket Sys ID];
    M --> N{Ticket Found?};
    N -- Yes --> O[Upload Screenshot to ServiceNow];
    O --> P{Upload Successful?};
    P -- Yes --> Q{Add Comment?};
    Q -- Yes --> R[Add Work Note to Ticket];
    Q -- No --> S[Update Status];
    R --> S;
    P -- No --> S[Update Status];
    N -- No --> S[Update Status];
    L -- No --> S[Update Status];
    K --> S[Update Status];
    S --> T[Ready];