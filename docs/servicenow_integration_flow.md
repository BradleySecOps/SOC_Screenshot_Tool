# ServiceNow Integration Flow

This flowchart details the process for configuring and interacting with ServiceNow from the tool.

```mermaid
graph TD
    A[Start Application] --> B{ServiceNow Configured?}
    B -- No --> C[Click Configure ServiceNow]
    C --> D[Open Configuration Window]
    D --> E[Enter Credentials]
    E --> F[Click Verify & Save]
    F --> G[Verify Credentials via API]
    G --> H{Verification Successful?}
    H -- Yes --> I["Update ServiceNow Status (Configured)"]
    H -- No --> J[Show Error Status]
    I --> B
    J --> E

    B -- Yes --> K[Enter Target INC/SIR #]
    K --> L[Click Save/Upload Button]
    L --> M{ServiceNow Configured?}
    M -- Yes --> N[Prompt for Password]
    N --> O[Get Ticket Sys ID via API]
    O --> P{Ticket Found?}
    P -- Yes --> Q[Upload Screenshot Attachment via API]
    Q --> R{Upload Successful?}
    R -- Yes --> S{Comment Provided?}
    S -- Yes --> T[Add Work Note via API]
    T --> U[Update Status]
    S -- No --> U
    R -- No --> U
    P -- No --> U
    M -- No --> V[Save Locally]
    V --> U
    U --> W[Process Complete]
